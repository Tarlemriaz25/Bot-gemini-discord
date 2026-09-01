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

# --- 2. KHỞI TẠO BOT & CẤU HÌNH ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 🆔 ĐIỀN ID DISCORD CỦA BRO VÀO ĐÂY (Thay dãy số bên dưới bằng ID thật)
MY_DISCORD_ID = 1352867812552736822

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
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_models = {}

# --- HÀM KIỂM TRA QUYỀN (CHỈ BRO HOẶC CHỦ SERVER MỚI ĐƯỢC DÙNG) ---
def is_owner_or_creator(interaction: discord.Interaction) -> bool:
    # Check nếu người dùng là chủ Server HOẶC là bro
    return interaction.user.id == interaction.guild.owner_id or interaction.user.id == MY_DISCORD_ID

# --- 3. HÀM GỌI GEMINI API ---
def generate_content_with_fallback(prompt, model_name):
    last_exception = None
    system_instruction = (
        "Bạn là một trợ lý AI cá nhân thông minh, am hiểu sâu sắc về công nghệ, phần cứng, lập trình, "
        "Hãy luôn suy luận cẩn thận, chi tiết, cung cấp giải pháp chính xác "
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
    custom_status = discord.CustomActivity(name="Quản lý Server & Trả lời AI ✨")
    await bot.change_presence(activity=custom_status)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"⚠️ Lỗi sync command: {e}")
    print(f"🚀 Bot đã online với tên: {bot.user}")

# --- 5. SLASH COMMANDS QUẢN LÝ (CHỈ CHO BRO & CHỦ SERVER) ---

# 👞 Lệnh Kick
@bot.tree.command(name="kick", description="Kick thành viên (Chỉ Admin Bot & Chủ Server dùng được)")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not is_owner_or_creator(interaction):
        await interaction.response.send_message("❌ Lệnh này chỉ dành riêng cho **Chủ Server** và **Admin Bot**!", ephemeral=True)
        return

    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👞 Đã kick **{member.name}**! Lý do: `{reason}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot không đủ quyền để kick người này (Role của họ cao hơn Bot)!", ephemeral=True)

# ⛔ Lệnh Ban
@bot.tree.command(name="ban", description="Ban thành viên (Chỉ Admin Bot & Chủ Server dùng được)")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not is_owner_or_creator(interaction):
        await interaction.response.send_message("❌ Lệnh này chỉ dành riêng cho **Chủ Server** và **Admin Bot**!", ephemeral=True)
        return

    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Đã BAN vĩnh viễn **{member.name}**! Lý do: `{reason}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot không đủ quyền để ban người này!", ephemeral=True)

# 🔇 Lệnh Timeout
@bot.tree.command(name="timeout", description="Mute thành viên (Chỉ Admin Bot & Chủ Server dùng được)")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Không có lý do"):
    if not is_owner_or_creator(interaction):
        await interaction.response.send_message("❌ Lệnh này chỉ dành riêng cho **Chủ Server** và **Admin Bot**!", ephemeral=True)
        return

    try:
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(f"🔇 Đã timeout **{member.name}** trong `{minutes}` phút! Lý do: `{reason}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bot không đủ quyền để timeout người này!", ephemeral=True)

# --- 6. COMMAND MODEL ---
@bot.tree.command(name="model", description="Chọn model Gemini bro muốn dùng")
@app_commands.choices(selected_model=[
    app_commands.Choice(name="Gemini 3.6 Flash (Nhanh & Chuẩn - Mặc định)", value="gemini-3.6-flash"),
    app_commands.Choice(name="Gemini 3.5 Flash-Lite (Ổn định)", value="gemini-3.5-flash-lite"),
    app_commands.Choice(name="Gemini 3.7 Flash (Thông minh hơn)", value="gemini-3.7-flash"),
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã đổi model cho bro **{interaction.user.name}** thành: `{selected_model.value}`!",
        ephemeral=True
    )

# --- 7. XỬ LÝ TIN NHẮN CHAT ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        current_model = user_models.get(message.author.id, "gemini-3.6-flash")

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
