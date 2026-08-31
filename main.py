import os
import threading
from datetime import timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# --- 1. SERVER GIẢ CHO RENDER ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- 2. KHỞI TẠO BOT & LẤY CÁC BIẾN MÔI TRƯỜNG ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

API_KEYS = []
key1 = os.getenv("GEMINI_API_KEY_1")
key2 = os.getenv("GEMINI_API_KEY_2")

if key1: API_KEYS.append(key1.strip())
if key2: API_KEYS.append(key2.strip())
if not API_KEYS:
    old_key = os.getenv("GEMINI_API_KEY")
    if old_key: API_KEYS.append(old_key.strip())

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Cần thiết để quản lý thành viên

bot = commands.Bot(command_prefix="!", intents=intents)
user_models = {}

# --- 3. HÀM GỌI GEMINI API ---
def generate_content_with_fallback(prompt, model_name):
    last_exception = None
    system_instruction = (
        "Bạn là một trợ lý AI cá nhân thông minh, am hiểu sâu sắc về công nghệ, phần cứng, lập trình, "
        "và hữu ích nhất. Trả lời bằng tiếng Việt hoặc tiếng Anh thân thiện, tự nhiên, trình bày đẹp mắt bằng Markdown."
    )
    
    for idx, key in enumerate(API_KEYS):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            print(f"⚠️ Key số {idx+1} gặp lỗi: {e}. Đang chuyển sang Key tiếp theo...")
            last_exception = e
            
    raise last_exception

# --- 4. SỰ KIỆN BOT ONLINE ---
@bot.event
async def on_ready():
    custom_status = discord.CustomActivity(name="I'm tired✨")
    await bot.change_presence(activity=custom_status)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"⚠️ Lỗi sync command: {e}")
    print(f"🚀 Bot đã online với tên: {bot.user}")

# --- 5. SLASH COMMANDS: QUẢN LÝ THÀNH VIÊN (KICK, BAN, TIMEOUT) ---

# 🔨 Lệnh Kick
@bot.tree.command(name="kick", description="Kick một thành viên ra khỏi server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👞 Đã kick **{member.name}** ra khỏi server! Lý do: `{reason}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot không đủ quyền để kick người này (Role của họ cao hơn Bot)!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

# ⛔ Lệnh Ban
@bot.tree.command(name="ban", description="Cấm (Ban) một thành viên khỏi server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Đã BAN vĩnh viễn **{member.name}**! Lý do: `{reason}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot không đủ quyền để ban người này!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

# 🔇 Lệnh Mute / Timeout
@bot.tree.command(name="timeout", description="Khóa mõm (Mute) thành viên trong số phút nhất định")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Không có lý do"):
    try:
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(f"🔇 Đã timeout **{member.name}** trong `{minutes}` phút! Lý do: `{reason}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot không đủ quyền để timeout người này!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

# --- 6. SLASH COMMAND CHỌN MODEL AI ---
@bot.tree.command(name="model", description="Chọn model Gemini bro muốn dùng")
@app_commands.choices(selected_model=[
    app_commands.Choice(name="Gemini 3.6 Flash (Nhanh & Chuẩn - Mặc định)", value="gemini-3.6-flash"),
    app_commands.Choice(name="Gemini 3.7 Flash (Ổn định)", value="gemini-3.7-flash"),
    app_commands.Choice(name="Gemini 3.5 Flash-Lite (Nhanh nhất)", value="gemini-3.5-flash-lite"),
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã đổi model cho **{interaction.user.name}** thành: `{selected_model.value}`!",
        ephemeral=True
    )

# --- 7. XỬ LÝ TIN NHẮN HỎI AI ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        current_model = user_models.get(message.author.id, "gemini-3.5-flash")

        async with message.channel.typing():
            try:
                reply = generate_content_with_fallback(prompt, current_model)

                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"❌ Lỗi API rồi bro ơi: {e}")

    await bot.process_commands(message)

# --- 8. CHẠY BOT ---
bot.run(DISCORD_TOKEN)
