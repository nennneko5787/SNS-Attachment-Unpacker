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
	select = []
	# 正規表現パターン
	pattern = r"https://www.deviantart.com/(.*)/art/(.*)"
	# マッチング
	matches = re.findall(pattern, message.content)
	for match in matches:
		select.append(discord.SelectOption(label=f"https://www.deviantart.com/{match[0]}/art/{match[1]}",value=f"https://www.deviantart.com/{match[0]}/art/{match[1]}",description="DeviantArtの画像を表示"))

	# 正規表現パターン
	pattern = r"https://(?:x\.com|twitter\.com)/(.*)/status/(.*)"
	# マッチング
	matches = re.findall(pattern, message.content)
	for match in matches:
		select.append(discord.SelectOption(label=f"https://x.com/{match[0]}/art/{match[1]}",value=f"https://x.com/{match[0]}/art/{match[1]}",description="Xの画像を表示"))
	view = discord.ui.View()
	view.add_item(discord.ui.Select(custom_id="linksel",options=select, min_values=1))
	await interaction.response.send_message("表示したい画像のリンクを選択してください。", view=view, ephemeral=True)

@client.event
async def on_interaction(interaction:discord.Interaction):
	try:
		# 2はボタン
		if interaction.data['component_type'] == 3:
			await on_dropdown(interaction)
	except KeyError:
		pass

async def on_dropdown(interaction: discord.Interaction):
	custom_id = interaction.data["custom_id"]
	if custom_id == "linksel":
		await interaction.response.defer()
		select_values = interaction.data["values"]
		url = select_values[0]
		try:
			fileList = []

			# 正規表現パターン
			pattern = r"https://www.deviantart.com/(.*)/art/(.*)"
			# マッチング
			matches = re.findall(pattern, url)

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
			matches = re.findall(pattern, url)

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

			if matched:
				await interaction.followup.send(files=fileList)
			else:
				await interaction.followup.send("SNSのリンクまたは画像が見つかりませんでした。", ephemeral=True)
		except:
			traceback_info = traceback.format_exc()
			await interaction.followup.send(f"処理を実行中にエラーが発生しました。\nhttps://github.com/nennneko5787/SNS-Attachment-Unpacker/issues/new にて以下のエラーログを添えて報告をお願いします。\n```\n{traceback_info}\n```", ephemeral=True)

@tasks.loop(seconds=20)
async def change_presence():
	game = discord.Game(f"{len(client.guilds)} SERVERS")
	await client.change_presence(status=discord.Status.idle, activity=game)

keep_alive()
client.run(token)