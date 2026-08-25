import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
from google import genai

# --- MỞ PORT GIẢ ĐỂ LỪA RENDER (GIÚP BOT KHÔNG BỊ KILL) ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Discord dang chay ngon lanh!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# Chạy server giả ở luồng phụ
threading.Thread(target=run_dummy_server, daemon=True).start()
# --------------------------------------------------------

# 1. Khởi tạo Token và Client
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 2. Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot đã online với tên: {bot.user}")

# 3. Lắng nghe tin nhắn
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        async with message.channel.typing():
            try:
                response = gemini_client.models.generate_content(
                    model='gemini-3.7-flash',
                    contents=prompt
                )

                reply = response.text

                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"Lỗi rồi bro: {e}")

    await bot.process_commands(message)

# 4. Chạy Bot
bot.run(DISCORD_TOKEN)
