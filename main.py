import os
import discord
from discord.ext import commands
from google import genai

# 1. Lấy Token và Key từ Environment Variables
discord_token = os.getenv("DISCORD_TOKEN")
gemini_key = os.getenv("GEMINI_API_KEY")

# 2. Khởi tạo Gemini Client
gemini_client = genai.Client(api_key=gemini_key)

# 3. Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot da online voi ten: {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Bỏ qua tin nhắn của chính bot

    # Chỉ phản hồi khi Tag tên bot hoặc dùng lệnh !ask
    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()
        
        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return
async with message.channel.typing():
        try:
            # Gọi API Gemini (dùng model chuẩn flash)
            response = gemini_client.models.generate_content(
                model='gemini-3.6-flash',
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
# 4. CHỈ CHẠY BOT Ở DÒNG CUỐI CÙNG NÀY
bot.run(discord_token)
