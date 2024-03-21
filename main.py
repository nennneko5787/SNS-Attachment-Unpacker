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
from yt_dlp import YoutubeDL

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
async def unpack(interaction: discord.Interaction, message: discord.Message):
	await interaction.response.defer(ephemeral=True)

	content = message.content

	select = []
	# 正規表現パターン
	pattern = r"https://www.deviantart.com/(.*)/art/(.*)"
	# マッチング
	matches = re.findall(pattern, content)
	for match in matches:
		select.append(discord.SelectOption(label=f"https://www.deviantart.com/{match[0]}/art/{match[1]}",value=f"https://www.deviantart.com/{match[0]}/art/{match[1]}",description="DeviantArtの画像を表示"))

	content = re.sub(pattern, "", content)

	# 正規表現パターン
	pattern = r"https://(?:x.com|twitter.com)/(.*)/status/(.*)"
	# マッチング
	matches = re.findall(pattern, content)
	for match in matches:
		select.append(discord.SelectOption(label=f"https://x.com/{match[0]}/status/{match[1]}",value=f"https://x.com/{match[0]}/status/{match[1]}",description="Xの画像を表示"))
	content = re.sub(pattern, "", content)

	# 正規表現パターン
	pattern = r"^(https?:\/\/[^\s\/$.?#].[^\s]*+\b)"
	# マッチング
	matches = re.findall(pattern, content)
	for match in matches:
		if await is_supported_by_yt_dlp(match) != None:
			select.append(discord.SelectOption(label=match,value=match,description="その他の対応しているSNSの添付ファイルを表示"))
	content = re.sub(pattern, "", content)

	if len(select) != 0:
		view = discord.ui.View()
		view.add_item(discord.ui.Select(custom_id="linksel",options=select, min_values=1))
		await interaction.followup.send("表示したい画像のリンクを選択してください。", view=view, ephemeral=True)
	else:
		await interaction.followup.send("このメッセージには添付ファイルを含んでいるURLがありません。")

@client.event
async def on_interaction(interaction:discord.Interaction):
	try:
		# 2はボタン
		if interaction.data['component_type'] == 3:
			await on_dropdown(interaction)
	except KeyError:
		pass

async def is_supported_by_yt_dlp(url):
	try:
		ydl_opts = {}
		loop = asyncio.get_event_loop()
		ydl = YoutubeDL(ydl_opts)
		dic = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
		# エラーが発生しない場合はURLを返す
		if dic.get("url",None) is not None:
			return {
				"url": dic.get("url",""),
				"content": dic.get("title","")
			}
		else:
			return None
	except:
		# エラーが発生した場合はNoneを返す
		return None

async def on_dropdown(interaction: discord.Interaction):
	custom_id = interaction.data["custom_id"]
	if custom_id == "linksel":
		await interaction.response.defer()
		select_values = interaction.data["values"]
		url = select_values[0]
		message = interaction.message
		content = ""
		try:
			fileList = []

			if "deviantart.com" in url:
				pattern = r"https://www.deviantart.com/(.*)/art/(.*)"
				match = re.match(pattern, url)

				if match:
					username = match[0]
					artwork_title = match[1]
					async with aiohttp.ClientSession() as session:
						async with session.get(f"https://backend.deviantart.com/oembed?url=https://www.deviantart.com/{username}/art/{artwork_title}") as response:
							json_data = await response.json()
							content = json_data.get("title","")
							file = await url_to_discord_file(json_data["url"])
							fileList.append(file)
			elif "twitter.com" in url or "x.com" in url:
				pattern = r"https://(?:x.com|twitter.com)/(.*)/status/(.*)"
				match = re.match(pattern, url)

				if match:
					username = match[0]
					post_id = match[1]
					async with aiohttp.ClientSession() as session:
						async with session.get(f"https://api.vxtwitter.com/{username}/status/{post_id}") as response:
							json_data = await response.json()
							content = re.sub(r"https://t\.co/[a-zA-Z0-9]+$", "", json_data.get("text",""))
							for f in json_data.get("mediaURLs",[]):
								file = await url_to_discord_file(f)
								fileList.append(file)
			else:
				fileList = []
				a = await is_supported_by_yt_dlp(url)
				if a != None:
					content = a.get("content")
					file = await url_to_discord_file(a.get("url"))
					fileList.append(file)
			await interaction.channel.send(f"{message.components[0]}")
			view = discord.ui.View()
			view.add_item(message.components[0].children[0])
			if len(fileList) > 0:
				await message.edit(content=content, attachments=fileList, view=view)
				# await interaction.followup.send(content=content, files=fileList, ephemeral=True)
			else:
				await message.edit(f"SNSのリンクまたは画像が見つかりませんでした。", attachments=[], view=view)
				# await interaction.followup.send(f"SNSのリンクまたは画像が見つかりませんでした。", ephemeral=True)
		except Exception as e:
			traceback_info = traceback.format_exc()
			await interaction.followup.send(f"処理を実行中にエラーが発生しました。\nhttps://github.com/nennneko5787/SNS-Attachment-Unpacker/issues/new にて以下のエラーログを添えて報告をお願いします。\n```\n{traceback_info}\n```", ephemeral=True)

@tasks.loop(seconds=20)
async def change_presence():
	game = discord.Game(f"{len(client.guilds)} SERVERS")
	await client.change_presence(status=discord.Status.online, activity=game)

keep_alive()
client.run(token)
