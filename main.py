import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# --- 1. MỞ PORT GIẢ CHO RENDER ---
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

# --- 2. KHỞI TẠO BOT & GEMINI ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Bộ nhớ lưu model được chọn của từng User (Mặc định là gemini-2.0-flash)
user_models = {}

@bot.event
async def on_ready():
    # Sync các Slash Command (dấu /) với Discord
    try:
        synced = await bot.tree.sync()
        print(f"Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"Lỗi sync command: {e}")
    print(f"Bot đã online: {bot.user}")

# --- 3. SLASH COMMAND: /model ---
@bot.tree.command(name="model", description="Chọn model Gemini bro muốn dùng")
@app_commands.choices(selected_model=[
    app_commands.Choice(name="Gemini 3.6 Flash (Nhanh & Chuẩn - Mặc định)", value="gemini-3.6-flash"),
    app_commands.Choice(name="Gemini 3.5 Flash-Lite (Ổn định nhanh nhất)", value="gemini-3.5-flash-lite"),
    app_commands.Choice(name="Gemini 3.1 Pro (Thông minh hơn, chậm hơn)", value="gemini-3.1-pro"),
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã đổi model cho bro **{interaction.user.name}** thành: `{selected_model.value}`!",
        ephemeral=True # Chỉ người bấm lệnh mới thấy tin nhắn này
    )

# --- 4. XỬ LÝ TIN NHẮN CHAT ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        # Lấy model user đã chọn, nếu chưa chọn thì lấy mặc định 2.0-flash
        current_model = user_models.get(message.author.id, "gemini-2.0-flash")

        async with message.channel.typing():
            try:
                response = gemini_client.models.generate_content(
                    model=current_model,
                    contents=prompt
                )

                reply = response.text

                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"Lỗi rồi bro ({current_model}): {e}")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
