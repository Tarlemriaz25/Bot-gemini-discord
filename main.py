import os
import discord
from discord.ext import commands
from google import genai

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
    # Không tự trả lời tin nhắn của chính bot
    if message.author == bot.user:
        return

    # Chỉ phản hồi khi được Tag tên bot hoặc dùng lệnh !ask
    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        async with message.channel.typing():
            try:
                # Gọi API Gemini (Dùng model chuẩn gemini-2.0-flash)
                response = gemini_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt
                )

                reply = response.text

                # Cắt nhỏ tin nhắn nếu dài hơn 2000 ký tự (giới hạn của Discord)
                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"Lỗi rồi bro: {e}")

    # Đảm bảo vẫn xử lý các lệnh khác nếu có
    await bot.process_commands(message)

# 4. Chạy Bot
bot.run(DISCORD_TOKEN)
