import os
import discord
from discord import app_commands
import aiohttp
from keep_alive import keep_alive
from discord.ext import tasks
import re
import asyncio
import io
import mimetypes
import traceback

if os.path.isfile(".env") == True:
	from dotenv import load_dotenv
	load_dotenv(verbose=True)

token = os.getenv('discord')	#Your TOKEN

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# 起動時に動作する処理
@client.event
async def on_ready():
	print("Ready!")
	change_presence.start()
	await tree.sync()	#スラッシュコマンドを同期

@tree.command(name="ping", description="ping")
async def ping(interaction: discord.Interaction):
	await interaction.response.send_message(f"🏓Pong! Ping: {client.latency}ms")

async def url_to_discord_file(url):
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			if response.status == 200:
				data = await response.read()
				content_type = response.headers.get("Content-Type")
				
				# MIMEタイプから拡張子を取得します
				extension = mimetypes.guess_extension(content_type)
				
				# ファイル名を作成します
				filename = f"file{extension}"
				
				# io.BytesIOを使ってバイトデータをラップします
				file_data = io.BytesIO(data)
				
				return discord.File(file_data, filename=filename)
			else:
				# リクエストが失敗した場合はエラーを処理します
				return None

@tree.context_menu(name="画像を展開")
async def delete(interaction: discord.Interaction, message: discord.Message):
	await interaction.response.send_message("しばらくお待ち下さい。処理が完了次第、DMにて画像を送信します。", ephemeral=True)
	try:
		fileList = []

		# 正規表現パターン
		pattern = r"https://www.deviantart.com/(.*)/art/(.*)"
		# マッチング
		matches = re.findall(pattern, message.content)

		matched = False

		if matches:
			matched = True
			for match in matches:
				# ユーザー名の取得
				username = match[0]
				
				# 作品タイトルの取得
				artwork_title = match[1]
				
				async with aiohttp.ClientSession() as session:
					async with session.get(f"https://backend.deviantart.com/oembed?url=https://www.deviantart.com/{username}/art/{artwork_title}") as response:
						json = await response.json()
						file = await url_to_discord_file(json["url"])
						fileList.append(file)

		# 正規表現パターン
		pattern = r"https://(?:x\.com|twitter\.com)/(.*)/status/(.*)"
		# マッチング
		matches = re.findall(pattern, message.content)

		if matches:
			matched = True
			for match in matches:
				print(match)

				# ユーザー名の取得
				username = match[0]
				
				# 投稿IDの取得
				post_id = match[1]
				
				async with aiohttp.ClientSession() as session:
					async with session.get(f"https://api.vxtwitter.com/{username}/status/{post_id}") as response:
						json = await response.json()
						for f in json["mediaURLs"]:
							fi = await url_to_discord_file(f)
							fileList.append(fi)

		if interaction.user.dm_channel == None:
			await interaction.user.create_dm()
		if matched:
			await interaction.user.dm_channel.send(f"元メッセージ: {message.jump_url}",files=fileList)
		else:
			await interaction.user.dm_channel.send("SNSのリンクまたは画像が見つかりませんでした。")
	except:
		traceback_info = traceback.format_exc()
		if interaction.user.dm_channel == None:
			await interaction.user.create_dm()
		await interaction.user.dm_channel.send(f"処理を実行中にエラーが発生しました。\nhttps://github.com/nennneko5787/SNS-Attachment-Unpacker/issues/new にて以下のエラーログを添えて報告をお願いします。\n```\n{traceback_info}\n```")

@tasks.loop(seconds=20)
async def change_presence():
	game = discord.Game(f"{len(client.guilds)} SERVERS")
	await client.change_presence(status=discord.Status.idle, activity=game)

keep_alive()
client.run(token)