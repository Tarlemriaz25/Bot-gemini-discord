import os
import discord
from discord.ext import commands
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Khởi tạo Gemini Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Cấu hình Discord Bot Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot da online voi ten: {bot.user}')

@bot.event
async def on_message(message):
    # Bỏ qua tin nhắn do chính Bot gửi
    if message.author == bot.user:
        return

    # Chỉ phản hồi khi Bot được tag tên hoặc tin nhắn bắt đầu bằng lệnh !ask
    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        # Loại bỏ phần tag bot hoặc lệnh !ask khỏi câu hỏi
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()
        
        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        async with message.channel.typing():
            try:
                # Gọi API Gemini
                response = gemini_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt
                )
                
                # Trả lời tin nhắn (cắt nhỏ nếu vượt quá giới hạn 2000 ký tự của Discord)
                reply = response.text
                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)
                    
            except Exception as e:
                await message.channel.send(f"Lỗi rồi bro: {e}")

    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
