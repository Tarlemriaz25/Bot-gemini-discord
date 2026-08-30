import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# --- 1. MỞ PORT GIẢ LỪA RENDER (GIÚP BOT KHÔNG BỊ KILL) ---
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

# Lấy 2 API Keys riêng biệt từ Render
API_KEYS = []
key1 = os.getenv("GEMINI_API_KEY_1")
key2 = os.getenv("GEMINI_API_KEY_2")

if key1: API_KEYS.append(key1.strip())
if key2: API_KEYS.append(key2.strip())

# Backup: Nếu bro vẫn dùng tên biến cũ GEMINI_API_KEY
if not API_KEYS:
    old_key = os.getenv("GEMINI_API_KEY")
    if old_key: API_KEYS.append(old_key.strip())

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Bộ nhớ lưu model được chọn của từng User
user_models = {}

# --- 3. HÀM GỌI API GEMINI VỚI SYSTEM PROMPT (THÔNG MINH HƠN) ---
def generate_content_with_fallback(prompt, model_name):
    last_exception = None
    
    # Chỉ thị hệ thống giúp bot trả lời thông minh, chuẩn xác như bản Web
    system_instruction = (
        "You are the smart AI, can shorten the answer, professional in programming."
        "You can only answer in English and Vietnamese"
    )
    
    for idx, key in enumerate(API_KEYS):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7 # Tăng tính tự nhiên, linh hoạt
                )
            )
            return response.text
        except Exception as e:
            print(f"⚠️ Key số {idx+1} gặp lỗi: {e}. Đang chuyển sang Key tiếp theo...")
            last_exception = e
            
    raise last_exception

# --- 4. SỰ KIỆN KHI BOT ONLINE (SYNC COMMAND & TẠO STATUS) ---
@bot.event
async def on_ready():
    # Cài đặt Custom Status (Dòng chữ cảm nghĩ dưới avatar)
    custom_status = discord.CustomActivity(name="!ask✨")
    await bot.change_presence(activity=custom_status)

    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"⚠️ Lỗi sync command: {e}")
        
    print(f"🚀 Bot đã online với tên: {bot.user} | Nạp thành công {len(API_KEYS)} API Key(s)")

# --- 5. SLASH COMMAND: /model ---
@bot.tree.command(name="model", description="Chọn model Gemini bro muốn dùng")
@app_commands.choices(selected_model=[
    app_commands.Choice(name="Gemini 3.6 Flash (Nhanh & Chuẩn - Mặc định)", value="gemini-3.6-flash"),
    app_commands.Choice(name="Gemini 3.5 Flash-Lite (Ổn định)", value="gemini-3.5-flash-lite"),
    app_commands.Choice(name="Gemini 3.7 Flash (Thông minh hơn)", value="gemini-3.7-flash"),
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã đổi model cho **{interaction.user.name}** thành: `{selected_model.value}`!",
        ephemeral=True
    )

# --- 6. XỬ LÝ TIN NHẮN CHAT ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Trả lời khi tag bot hoặc gõ !ask
    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        current_model = user_models.get(message.author.id, "gemini-3.6-flash")

        async with message.channel.typing():
            try:
                reply = generate_content_with_fallback(prompt, current_model)

                # Chia nhỏ tin nhắn nếu dài hơn 2000 ký tự
                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"❌ Tất cả API Key đều bị lỗi hoặc hết quota bro ơi: {e}")

    await bot.process_commands(message)

# --- 7. CHẠY BOT ---
bot.run(DISCORD_TOKEN)
