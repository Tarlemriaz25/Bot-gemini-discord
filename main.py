import os
import threading
from datetime import timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands

# 1. SDK CỦA CÁC BÊN AI
from google import genai
from openai import OpenAI
import anthropic

# --- 1. SERVER GIẢ CHO RENDER ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Multi-AI is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- 2. KHỞI TẠO BIẾN MÔI TRƯỜNG & BOT ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MY_DISCORD_ID = 123456789012345678  # 🆔 Đổi thành ID Discord của bro

# 🔑 Gemini Keys
GEMINI_KEYS = []
g_key1 = os.getenv("GEMINI_API_KEY_1")
g_key2 = os.getenv("GEMINI_API_KEY_2")
if g_key1: GEMINI_KEYS.append(g_key1.strip())
if g_key2: GEMINI_KEYS.append(g_key2.strip())

# 🔑 OpenAI & Claude Keys
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_models = {}

# System Instruction chung cho mọi AI
SYSTEM_PROMPT = (
    "Bạn là một trợ lý AI cá nhân thông minh, am hiểu sâu sắc về công nghệ, phần cứng, lập trình, "
    "và hệ thống Android/Linux. Hãy luôn suy luận cẩn thận, chi tiết, cung cấp giải pháp chính xác "
    "và hữu ích nhất. Trả lời bằng tiếng Việt thân thiện, tự nhiên, trình bày đẹp mắt bằng Markdown."
)

def is_owner_or_creator(interaction: discord.Interaction) -> bool:
    return interaction.user.id == interaction.guild.owner_id or interaction.user.id == MY_DISCORD_ID

# --- 3. HÀM ĐIỀU HƯỚNG GỌI AI LINH HOẠT ---
def ask_ai(prompt, model_name):
    # --- A. NHÓM MODEL GEMINI ---
    if model_name.startswith("gemini"):
        last_exception = None
        for key in GEMINI_KEYS:
            try:
                client = genai.Client(api_key=key)
                res = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.7
                    )
                )
                return res.text
            except Exception as e:
                last_exception = e
        raise last_exception or Exception("Không có Gemini API Key hợp lệ.")

    # --- B. NHÓM MODEL CHATGPT (OPENAI) ---
    elif model_name.startswith("gpt"):
        if not OPENAI_KEY:
            raise Exception("Chưa cấu hình OPENAI_API_KEY trên Render!")
        
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

    # --- C. NHÓM MODEL CLAUDE (ANTHROPIC) ---
    elif model_name.startswith("claude"):
        if not ANTHROPIC_KEY:
            raise Exception("Chưa cấu hình ANTHROPIC_API_KEY trên Render!")
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model=model_name,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text

    else:
        raise Exception("Model không hợp lệ!")

# --- 4. SỰ KIỆN BOT ONLINE ---
@bot.event
async def on_ready():
    custom_status = discord.CustomActivity(name="Multi-AI Manager (Gemini/GPT/Claude) ✨")
    await bot.change_presence(activity=custom_status)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"⚠️ Lỗi sync command: {e}")
    print(f"🚀 Bot đã online thành công!")

# --- 5. SLASH COMMAND CHỌN MODEL AI ---
@bot.tree.command(name="model", description="Chọn mô hình AI từ Google, OpenAI hoặc Anthropic")
@app_commands.choices(selected_model=[
    # Google Gemini
    app_commands.Choice(name="[Google] Gemini 3.6 Flash (Nhanh - Mặc định)", value="gemini-2.0-flash"),
    app_commands.Choice(name="[Google] Gemini 3.5 Flash-Lite (Thông minh)", value="gemini-1.5-pro"),
    
    # OpenAI ChatGPT
    app_commands.Choice(name="[OpenAI] GPT-4o Mini (Nhanh, Rẻ)", value="gpt-4o-mini"),
    app_commands.Choice(name="[OpenAI] GPT-4o (Thông minh cao)", value="gpt-4o"),
    
    # Anthropic Claude
    app_commands.Choice(name="[Claude] Claude 3.5 Haiku (Siêu nhanh)", value="claude-3-5-haiku-20241022"),
    app_commands.Choice(name="[Claude] Claude 3.5 Sonnet (Viết lách/Code đỉnh)", value="claude-3-5-sonnet-20241022")
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã chuyển model sang: **{selected_model.name}** (`{selected_model.value}`)",
        ephemeral=True
    )

# --- 6. QUẢN LÝ THÀNH VIÊN (KICK, BAN, TIMEOUT) ---
@bot.tree.command(name="kick", description="Kick thành viên (Chỉ Bro & Chủ Server)")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not is_owner_or_creator(interaction):
        await interaction.response.send_message("❌ Lệnh dành riêng cho Chủ Server và Admin Bot!", ephemeral=True)
        return
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👞 Đã kick **{member.name}**! Lý do: `{reason}`")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban thành viên (Chỉ Bro & Chủ Server)")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
    if not is_owner_or_creator(interaction):
        await interaction.response.send_message("❌ Lệnh dành riêng cho Chủ Server và Admin Bot!", ephemeral=True)
        return
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Đã BAN **{member.name}**! Lý do: `{reason}`")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout thành viên (Chỉ Bro & Chủ Server)")
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Không có lý do"):
    if not is_owner_or_creator(interaction):
        await interaction.response.send_message("❌ Lệnh dành riêng cho Chủ Server và Admin Bot!", ephemeral=True)
        return
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(f"🔇 Đã timeout **{member.name}** trong `{minutes}` phút! Lý do: `{reason}`")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

# --- 7. XỬ LÝ CHAT NÓI CHUYỆN ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        current_model = user_models.get(message.author.id, "gemini-2.0-flash")

        async with message.channel.typing():
            try:
                reply = ask_ai(prompt, current_model)

                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"❌ Lỗi xử lý AI: {e}")

    await bot.process_commands(message)

# --- 8. CHẠY BOT ---
bot.run(DISCORD_TOKEN)
