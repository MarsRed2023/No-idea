import discord
from discord import app_commands
import wikipedia
import re
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from difflib import SequenceMatcher
import fandom
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from fuzzywuzzy import process
import ssl
import certifi
import random
import time
import asyncio
from googletrans import Translator
from googletrans import LANGUAGES
import yt_dlp
import subprocess
import tempfile
import os
from discord.ui import Button, View
import aiohttp
import urllib.parse

ssl_context = ssl.create_default_context(cafile=certifi.where())

quotes = [
    "The only way to do great work is to love what you do. – Steve Jobs",
    "Success is not the key to happiness. Happiness is the key to success. – Albert Schweitzer",
    "Believe you can and you're halfway there. – Theodore Roosevelt",
    "It does not matter how slowly you go as long as you do not stop. – Confucius",
    "You are never too old to set another goal or to dream a new dream. – C.S. Lewis",
    "The future belongs to those who believe in the beauty of their dreams. – Eleanor Roosevelt",
    "It always seems impossible until it's done. – Nelson Mandela",
    "The only limit to our realization of tomorrow is our doubts of today. – Franklin D. Roosevelt",
    "Act as if what you do makes a difference. It does. – William James",
    "Success is not final, failure is not fatal: It is the courage to continue that counts. – Winston Churchill"
]

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Logged in as {self.user}!')  
        # Synchronize commands with Discord's servers
        await self.tree.sync()

bot = MyBot()

# Slash Command: /ping
@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🍓")

# Slash Command: /create_channel
@bot.tree.command(name="create_channel", description="Create a new channel (text or voice).")
@app_commands.choices(channel_type=[
    app_commands.Choice(name="Text", value="text"),
    app_commands.Choice(name="Voice", value="voice")
])  
async def create_channel(interaction: discord.Interaction, channel_name: str, channel_type: app_commands.Choice[str]):
    guild = interaction.guild
    if guild:
        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        if not existing_channel:
            if channel_type.value == "text":
                await guild.create_text_channel(channel_name)
            elif channel_type.value == "voice":
                await guild.create_voice_channel(channel_name)
            await interaction.response.send_message(f'Channel "{channel_name}" ({channel_type.name}) created!')
        else:
            await interaction.response.send_message(f'Channel "{channel_name}" already exists!')



@bot.tree.command(name="wiki", description="Get information about a topic from Wikipedia.")
async def wiki(interaction: discord.Interaction, query: str):
    try:
        # Defer the response if processing might take time
        await interaction.response.defer()

        # First, attempt to get Wikipedia search results
        search_results = wikipedia.search(query)

        if not search_results:
            await interaction.followup.send("Sorry, I couldn't find anything on that topic.")
            return

        # Try to find the exact match by checking all search results
        exact_match_found = False
        for result in search_results:
            if result.lower() == query.lower():
                best_match = result
                exact_match_found = True
                break

        # If no exact match is found, proceed with fuzzy matching
        if not exact_match_found:
            best_match = process.extractOne(query, search_results)
            # Apply a stricter threshold to avoid irrelevant fuzzy matches
            if best_match[1] < 80:
                await interaction.followup.send(f"Did you mean: {best_match[0]}?")
                return
            best_match = best_match[0]

        # Fetch the summary for the best match found
        summary = wikipedia.summary(best_match, sentences=2)
        await interaction.followup.send(f'**{best_match}**\n{summary}')

    except wikipedia.exceptions.DisambiguationError as e:
        await interaction.followup.send(f'Topic is ambiguous. Did you mean: {", ".join(e.options[:5])}?')
    except wikipedia.exceptions.PageError:
        await interaction.followup.send("Sorry, no Wikipedia page found for that topic.")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")
        
# Function to calculate text similarity
def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

@bot.tree.command(name="youtube", description="Search for a video on YouTube using the official API and return the most relevant result.")
async def youtube(interaction: discord.Interaction, query: str):
    # Your YouTube Data API key
    api_key = 'AIzaSyC5dCMvK9z51NimCixOKr-uqfRZcZoukEM'

    # Build the YouTube API client
    youtube = build("youtube", "v3", developerKey=api_key)

    # Search for videos using the query
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=5  # Fetch top 5 results for better comparison
    )

    # Execute the request
    response = request.execute()

    # If there are no results, notify the user
    if 'items' not in response or len(response['items']) == 0:
        await interaction.response.send_message("No results found.")
        return

    # Track the most relevant video
    best_match = None
    best_similarity = 0

    # Go through each video and compare the query with title and description
    for video in response['items']:
        title = video['snippet']['title']
        description = video['snippet']['description']
        
        # Calculate the similarity score based on the title and description
        title_similarity = similarity(query.lower(), title.lower())
        description_similarity = similarity(query.lower(), description.lower())
        
        # Combine both scores for a final similarity score
        total_similarity = (title_similarity + description_similarity) / 2
        
        # Update best match if the current video is more relevant
        if total_similarity > best_similarity:
            best_similarity = total_similarity
            best_match = video

    # If we found a match, send the video URL
    if best_match:
        video_url = f"https://www.youtube.com/watch?v={best_match['id']['videoId']}"
        await interaction.response.send_message(f"Here's the most relevant video I found: {video_url}")
    else:
        await interaction.response.send_message("Couldn't find a highly relevant match.")

# Set your OpenAI API key
API_KEY = 'AIzaSyDsyQEyfPn218rd-ubd-QE7AZveJ7FcRng'
CX = '6773220f0984546d5!!'
@bot.tree.command(name="google_search", description="Search Google and return the first result.")
async def google_search(interaction: discord.Interaction, query: str):
    search_url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={API_KEY}&cx={CX}"

    # Make the GET request to Google's Custom Search API
    response = requests.get(search_url)

    if response.status_code == 200:
        search_results = response.json()

        # Extract the first result (if any)
        items = search_results.get('items', [])
        if items:
            first_result = items[0]
            title = first_result['title']
            link = first_result['link']
            await interaction.response.send_message(f"Found result: {title}\n{link}")
        else:
            await interaction.response.send_message("No results found.")
    else:
        await interaction.response.send_message(f"Error fetching search results. Status code: {response.status_code}")

# Async function to fetch a random quote from an online API
async def fetch_quote():
    url = "https://zenquotes.io/api/random"  # ZenQuotes API URL
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # Extract the quote and author from the JSON response
                quote = data[0]['q']
                author = data[0]['a']
                return f'"{quote}" – {author}'
            else:
                return "Sorry, I couldn't fetch a quote at the moment."

@bot.tree.command(name="inspire", description="Get an inspirational quote.")
async def inspire(interaction: discord.Interaction):
    # Fetch a random quote using the async function
    quote = await fetch_quote()
    # Send the fetched quote to the user
    await interaction.response.send_message(quote)

@bot.tree.command(name="rock_paper_scissors", description="Play Rock Paper Scissors with the bot.")
@app_commands.choices(choice=[
    app_commands.Choice(name="Rock", value="rock"),
    app_commands.Choice(name="Paper", value="paper"),
    app_commands.Choice(name="Scissors", value="scissors")
])
async def rock_paper_scissors(interaction: discord.Interaction, choice: app_commands.Choice[str]):
    user_choice = choice.value
    bot_choice = random.choice(["rock", "paper", "scissors"])
    
    # Determine the result
    if user_choice == bot_choice:
        result = "It's a tie!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        result = f"You win! I chose {bot_choice}."
    else:
        result = f"You lose! I chose {bot_choice}."
    
    # Send response
    await interaction.response.send_message(f"You chose {user_choice}. {result}")

@bot.tree.command(name="set_timer", description="Set a timer and get a formatted Unix timestamp.")
async def set_timer(interaction: discord.Interaction, days: int, hours: int, minutes: int, seconds: int, milliseconds: int = 0):
    # Calculate the total time in seconds (including milliseconds)
    total_seconds = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds + (milliseconds / 1000)
    
    # Get the current time (Unix timestamp) and add the total_seconds to it
    current_timestamp = time.time()
    target_timestamp = current_timestamp + total_seconds

    # Format the target timestamp for Discord (including seconds)
    discord_timestamp = f"<t:{int(target_timestamp)}:R>"  # "R" gives relative time (e.g., "in 1 hour")
    
    # Optionally, you can also send the exact formatted timestamp like this:
    formatted_time = f"<t:{int(target_timestamp)}:F>"  # "F" gives the full date and time

    # Send response
    await interaction.response.send_message(f"Timer set! {discord_timestamp}\n {formatted_time}")

bad_jokes = [
    "Why don't skeletons fight each other? They don't have the guts.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "I would tell you a joke about an elevator, but it's an uplifting experience.",
    "Why don’t eggs tell jokes? They’d crack each other up.",
    "I asked my dog what’s two minus two. He said nothing.",
    "I used to play piano by ear, but now I use my hands.",
    "I couldn't figure out how to put my seatbelt on... then it clicked.",
    "Why don’t some couples go to the gym? Because some relationships don’t work out.",
    "I told my computer I needed a break, and now it won’t stop sending me Kit-Kats.",
    "I’m reading a book about anti-gravity. It’s impossible to put down.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why don’t oysters donate to charity? Because they’re shellfish.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
    "I tried to start a band called 1023MB… we haven’t got a gig yet.",
    "I’m on a whiskey diet. I’ve lost three days already.",
    "I’m no good at math, but I’m great at making bad jokes.",
    "What’s orange and sounds like a parrot? A carrot.",
    "I’m reading a book on anti-gravity. It’s impossible to put down.",
    "What do you call fake spaghetti? An impasta!",
    "Why don’t skeletons fight each other? They don’t have the guts.",
    "I tried to catch some fog earlier... I mist.",
    "I used to be a baker, but I couldn't make enough dough.",
    "Did you hear about the mathematician who’s afraid of negative numbers? He'll stop at nothing to avoid them.",
    "What’s the best way to watch a fly fishing tournament? Live stream.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why don't skeletons fight each other? They don't have the guts.",
    "I can't trust stairs because they're always up to something.",
    "I couldn't figure out how to put my seatbelt on... then it clicked.",
    "I don't trust people who do acupuncture... they're back stabbers.",
    "I can't believe I got fired from the calendar factory... all I did was take a day off.",
    "I used to be addicted to soap, but now I'm clean.",
    "I only know 25 letters of the alphabet. I don't know y.",
    "How do you organize a space party? You planet.",
    "I don’t play soccer because I enjoy the sport. I just do it for kicks.",
    "I can’t believe I got fired from the bakery. They said I wasn’t kneaded.",
    "I used to be a professional boxer, but I had to quit because I couldn’t take the punches.",
    "I tried to start a hot air balloon business, but it never really took off.",
    "I used to be a baker, but I couldn’t make enough dough.",
    "Why don’t skeletons ever use cell phones? They don’t have the nerve.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why was the math book sad? Because it had too many problems.",
    "I can't believe I got fired from the calendar factory... all I did was take a day off.",
    "I used to be a baker, but I couldn't make enough dough.",
    "I used to be a baker, but I couldn’t make enough dough.",
    "What do you call an alligator in a vest? An investigator.",
    "I’m on a seafood diet. I see food and I eat it.",
    "I don’t trust people who do acupuncture... they’re back stabbers.",
    "I used to be addicted to soap, but now I'm clean.",
    "How does a penguin build its house? Igloos it together.",
    "I don't trust people who do acupuncture... they're back stabbers.",
    "I can’t believe I got fired from the calendar factory... all I did was take a day off.",
    "I tried to start a hot air balloon business, but it never really took off.",
    "I used to be a baker, but I couldn't make enough dough.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "I don’t trust people who do acupuncture... they’re back stabbers.",
    "Why don’t skeletons fight each other? They don’t have the guts.",
    "I used to play piano by ear, but now I use my hands."
]

# Define the bad_jokes command
@bot.tree.command(name="bad_jokes", description="Hear a bad joke!")
async def bad_jokes_command(interaction: discord.Interaction):
    joke = random.choice(bad_jokes)  # Pick a random joke
    await interaction.response.send_message(joke)

@bot.tree.command(name="ask_question", description="Ask the Magic 8-ball a question!")
async def ask_question(interaction: discord.Interaction, question: str):
    responses = [
        "Yes.",
        "No.",
        "Maybe.",
        "Ask again later.",
        "Definitely not.",
        "It is certain.",
        "Cannot predict now."
    ]
    response = random.choice(responses)
    await interaction.response.send_message(f"Your question: {question}\nAnswer: {response}")

@bot.tree.command(name="flip_coin", description="Flip a coin!")
async def flip_coin(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"The coin landed on: {result}")

@bot.tree.command(name="roll_dice", description="Roll a 6-sided dice!")
async def roll_dice(interaction: discord.Interaction):
    result = random.randint(1, 6)
    await interaction.response.send_message(f"You rolled: {result}")

@bot.tree.command(name="remind_me", description="Set a reminder!")
async def remind_me(interaction: discord.Interaction, time: int, task: str):
    await interaction.response.send_message(f"Reminder set for {time} minutes. I'll remind you about: {task}")
    await asyncio.sleep(time * 60)  # Wait for the specified time
    await interaction.user.send(f"Reminder: {task}")

@bot.tree.command(name="server_info", description="Get information about this server.")
async def server_info(interaction: discord.Interaction):
    guild = interaction.guild
    member_count = guild.member_count
    creation_date = guild.created_at.strftime('%Y-%m-%d')
    await interaction.response.send_message(f"Server name: {guild.name}\nMember count: {member_count}\nCreated on: {creation_date}")

translator = Translator()



# Define language abbreviation to full name mapping using googletrans LANGUAGES
# We will reverse this to match the full language name to code
language_map = {v.lower(): k for k, v in LANGUAGES.items()}

@bot.tree.command(name="translate", description="Translate text to a desired language.")
async def translate(interaction: discord.Interaction, text: str, target_language: str):
    # Normalize target language to lowercase and check if it's valid
    target_language = target_language.lower()

    if target_language not in language_map:
        await interaction.response.send_message(f"Sorry, I don't recognize the language name `{target_language}`.")
        return

    # Get the corresponding language code from the map
    language_code = language_map[target_language]

    # Translate the text
    translated_text = translator.translate(text, dest=language_code)
    
    # Send the translated message
    await interaction.response.send_message(f"Translated text to {LANGUAGES[language_code]}: {translated_text.text}")


@bot.tree.command(name="cat_fact", description="Sends a random cat fact")
async def cat_fact(interaction: discord.Interaction):
    facts = [
    "Cats are the most popular pet in the United States: There are approximately 88 million pet cats compared to 74 million pet dogs.",
    "Cats have over 20 muscles that control their ears: This allows them to rotate their ears 180 degrees and move them independently.",
    "Cats sleep 70 percent of their lives: That's about 16 hours a day!",
    "A group of cats is called a clowder: Other terms include a clowder of cats, a clutter of cats, a pounce of cats, and a glaring of cats.",
    "Cats have fewer taste buds than dogs or people: They have about 473 taste buds, while humans have 9,000 and dogs have 1,700.",
    "Cats don't get cavities: While they can suffer from other dental issues, they don't get cavities like humans do.",
    "Cats can jump five times their own height: This impressive ability is due to their powerful hind leg muscles.",
    "Cats have 230 bones: That's 24 more than humans.",
    "Cats make over 100 different vocal sounds: While dogs make around 10, cats have a vast range of vocalizations.",
    "Cats can be toilet-trained: With patience and the right training, cats can learn to use a human toilet.",
    "Cats have a specialized collarbone: This allows them to always land on their feet when they fall.",
    "Cats have a third eyelid: Known as the haw, it helps protect their eyes and keep them moist.",
    "Cats can run up to 30 mph: This makes them excellent hunters and escape artists.",
    "Cats have whiskers on the backs of their front legs: These whiskers help them sense their environment and navigate tight spaces.",
    "Cats can make a chirping sound: This is often heard when they see birds or small prey animals.",
    "Cats have a specialized tongue: Their rough, spiny texture helps them groom themselves and scrape meat off bones.",
    "Most cats have five toes on their front paws: However, some cats are polydactyl, having extra toes.",
    "A cat’s nose has a unique pattern: Much like human fingerprints, no two cats’ noses are alike.",
    "Cats' purring frequency has been shown to reduce stress and help with healing.",
    "The oldest cat ever recorded lived to 38 years and 3 days.",
    "A cat’s whiskers are not just for measuring space, they also help with balance.",
    "Cats can make themselves appear larger when they feel threatened by puffing up their fur.",
    "A cat’s hearing range is between 48 Hz to 85 kHz, which is far beyond the human range.",
    "Cats have an extraordinary ability to see in low light, enabling them to hunt in the dark.",
    "The average cat sleeps 12-16 hours a day, but some breeds can sleep even more.",
    "The Maine Coon is one of the largest domestic cat breeds.",
    "Cats can’t taste sweet things: Their taste buds do not detect sweetness.",
    "A cat’s vision is specialized for detecting movement, even in the dark.",
    "Cats use their tail to communicate: A straight-up tail is a sign of happiness and confidence.",
    "The Sphynx cat is hairless, but they still need to be bathed regularly.",
    "Cats were worshipped in ancient Egypt, and killing a cat was punishable by death.",
    "Each cat has a unique meow: They may develop their own personal 'vocabulary' with their owners.",
    "Cats rub against you to mark their territory: This is a behavior called bunting.",
    "Some cats enjoy water: Certain breeds, like the Turkish Van, are known to be fond of swimming.",
    "When a cat blinks slowly at you, it's a sign of affection.",
    "A cat’s liver can metabolize alcohol differently than humans, making it more dangerous for them.",
    "The average cat walks on their toes, making them digitigrades.",
    "Cats can be allergic to humans, but it's rare.",
    "A cat’s heart beats twice as fast as a human's heart.",
    "A house cat is faster than an Olympic sprinter: They can run at speeds of up to 30 miles per hour.",
    "The largest wildcat species is the Siberian tiger, which can weigh up to 900 pounds.",
    "Unlike dogs, cats are not pack animals; they are solitary by nature.",
    "Cats use their claws for more than just scratching; they also use them for climbing and hunting.",
    "A cat’s purr can have a calming effect on humans, lowering blood pressure and promoting relaxation.",
    "In Japan, cats are considered good luck, and they are often kept as pets to attract good fortune.",
    "There is a breed of cat called the 'American Curl' that has ears that curl backward.",
    "A cat can run at speeds of up to 30 mph for short distances.",
    "A cat’s whiskers are incredibly sensitive: They help cats detect changes in their surroundings and judge whether they can fit through a space.",
    "Kittens are born blind and deaf: They don’t open their eyes or ears until around two weeks of age."
]


    # Send a random question
    await interaction.response.send_message(random.choice(facts))


class TruthOrDareView(View):
    def __init__(self):
        super().__init__()

        # Define the truths and dares lists
        self.truths = [
            "What’s your biggest fear?",
            "Have you ever lied to your best friend?",
            "What’s the most embarrassing thing you’ve ever done?",
            "What’s a secret you’ve never told anyone?",
            "What’s something you’ve never told your parents?",
            "Who do you have a crush on right now?",
            "What’s something you’re insecure about?",
            "If you could change one thing about your life, what would it be?",
            "Have you ever cheated on a test?",
            "What’s the weirdest dream you’ve ever had?",
            "If you could swap lives with someone for a day, who would it be?",
            "Have you ever kissed someone of the same sex?",
            "What’s the most rebellious thing you’ve ever done?",
            "What’s your guilty pleasure?",
            "What’s the craziest thing you’ve done for love?",
            "Have you ever stolen something?",
            "What’s the worst thing you’ve ever said to someone?",
            "If you could erase one memory, what would it be?",
            "What’s your biggest regret?",
            "What’s your worst habit?",
            "Have you ever gotten into trouble with the police?",
            "What’s the worst lie you’ve ever told?",
            "Who in your life do you feel the most grateful for?",
            "What’s the most awkward thing you’ve done at school?",
            "What’s the longest time you’ve gone without showering?",
            "What’s the worst thing you’ve ever done to a friend?",
            "What’s a talent you have that nobody knows about?",
            "What’s the most embarrassing song on your playlist?",
            "What’s the last thing you Googled?",
            "What’s something you’re afraid of people finding out about you?",
            "What’s something you’ve done that you wish you could forget?",
            "If you could switch lives with anyone in the world, who would it be?",
            "What’s the biggest lie you’ve told your parents?",
            "What’s the most embarrassing text you’ve sent?",
            "What’s the most ridiculous thing you’ve ever done in public?",
            "What’s the dumbest thing you’ve ever done for love?",
            "Have you ever been caught doing something you shouldn’t?",
            "What’s the most awkward thing that’s happened to you in public?",
            "What’s something you wish people knew about you but you’re too afraid to tell them?",
            "If you could be famous for one thing, what would it be?",
        ]

        self.dares = [
            "Dance like nobody's watching for one minute.",
            "Post an embarrassing photo on your social media.",
            "Do 20 pushups in a row.",
            "Try to lick your elbow.",
            "Send a text to the last person you texted saying, 'I need help!'",
            "Let someone else draw on your face with a marker.",
            "Do your best impression of someone in the room.",
            "Call a random contact and sing 'Happy Birthday' to them.",
            "Speak in an accent (French, British, etc.) for the next 5 minutes.",
            "Do 50 jumping jacks.",
            "Let someone else write a message on your forehead with a marker.",
            "Wear socks on your hands for the next 5 minutes.",
            "Pretend to be a waiter/waitress and take everyone's orders.",
            "Take a silly selfie and send it to your best friend.",
            "Imitate a celebrity for the next 3 minutes.",
            "Try to touch your toes with your tongue.",
            "Run around your house three times.",
            "Do your best impression of a cat for 1 minute.",
            "Post a video of yourself singing a song of someone else's choice.",
            "Take a shot of hot sauce.",
            "Let someone text anyone in your contacts.",
            "Record yourself talking to a pet in a silly voice for 30 seconds.",
            "Call your crush and tell them how you feel.",
            "Do your best dance move for 2 minutes straight.",
            "Wear an embarrassing outfit and walk around the house for 10 minutes.",
            "Post a video of yourself doing 30 pushups on social media.",
            "Read the last text you sent out loud.",
            "Imitate someone in the group for 2 minutes.",
            "Speak in a foreign language for the next 10 minutes.",
            "Draw a silly picture and post it online.",
            "Pretend to be a waiter/waitress and serve someone else in the room.",
            "Do 10 cartwheels in a row.",
            "Do your best impression of a baby crying for 2 minutes.",
            "Let someone else take over your social media for the next 5 minutes.",
            "Wear a funny wig for the next 10 minutes.",
            "Jump up and down 50 times.",
            "Do a dramatic reading of a random text message you’ve received.",
            "Post a silly meme on your story.",
            "Text your crush saying, 'I have something important to tell you.'",
            "Post a picture of your pet on your story.",
            "Let someone tickle you for 30 seconds.",
            "Talk in a funny voice for the next 10 minutes.",
            "Try to juggle three things at once.",
            "Send a funny meme to a random friend.",
            "Try to balance a spoon on your nose for 30 seconds.",
            "Pretend you are a news anchor and report the weather.",
            "Dance to a song with no music.",
        ]

    @discord.ui.button(label="Truth", style=discord.ButtonStyle.primary)
    async def truth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Choose a random truth from the list
        truth = random.choice(self.truths)
        await interaction.response.send_message(f"Truth: {truth}")

    @discord.ui.button(label="Dare", style=discord.ButtonStyle.danger)
    async def dare_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Choose a random dare from the list
        dare = random.choice(self.dares)
        await interaction.response.send_message(f"Dare: {dare}")

    @discord.ui.button(label="Random", style=discord.ButtonStyle.secondary)
    async def random_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Randomly choose between truth or dare
        if random.choice([True, False]):
            truth = random.choice(self.truths)
            await interaction.response.send_message(f"Truth: {truth}")
        else:
            dare = random.choice(self.dares)
            await interaction.response.send_message(f"Dare: {dare}")

@bot.tree.command(name="truth_or_dare", description="Play Truth or Dare!")
async def truth_or_dare(interaction: discord.Interaction):
    view = TruthOrDareView()
    await interaction.response.send_message("Choose your fate!", view=view)


class TriviaButtonView(View):
    def __init__(self, question_data, category, difficulty):
        super().__init__()
        self.question_data = question_data
        self.category = category
        self.difficulty = difficulty
        self.correct_answer = question_data['correct']

async def send_feedback(self, interaction, is_correct):
    if is_correct:
        await interaction.followup.send("Correct! 🎉")  # Correct response
    else:
        await interaction.followup.send(f"Wrong! The correct answer was {self.correct_answer}.")  # Wrong answer response
    await self.stop()


# Trivia data
laws_trivia = {
    "easy": [
        {"question": "What is the legal drinking age in the United States?", 
         "answers": ["18", "21", "25", "30"], "correct": "21"},
        {"question": "What is the maximum speed limit on highways in most of the USA?", 
         "answers": ["55 mph", "65 mph", "75 mph", "80 mph"], "correct": "65 mph"},
    ],
    "medium": [
        {"question": "Which country legalized same-sex marriage first?", 
         "answers": ["USA", "Canada", "Netherlands", "Germany"], "correct": "Netherlands"},
    ],
    "hard": [
        {"question": "What is the legal document that governs the rights of workers in European Union countries?", 
         "answers": ["The European Charter", "The European Social Charter", "The EU Rights Act", "The Common Rights Document"], "correct": "The European Social Charter"},
    ]
}

geography_trivia = {
    "easy": [
        {"question": "What is the capital of France?", 
         "answers": ["London", "Berlin", "Paris", "Rome"], "correct": "Paris"},
        {"question": "Which continent is Brazil located in?", 
         "answers": ["Africa", "Asia", "South America", "Europe"], "correct": "South America"},
    ],
    "medium": [
        {"question": "What is the longest river in the world?", 
         "answers": ["Amazon", "Nile", "Yangtze", "Ganges"], "correct": "Nile"},
    ],
    "hard": [
        {"question": "Which country has the most official languages?", 
         "answers": ["Switzerland", "India", "South Africa", "Belgium"], "correct": "South Africa"},
    ]
}

history_trivia = {
    "easy": [
        {"question": "Who was the first President of the United States?", 
         "answers": ["George Washington", "Abraham Lincoln", "Thomas Jefferson", "John Adams"], "correct": "George Washington"},
        {"question": "In what year did World War II end?", 
         "answers": ["1941", "1945", "1950", "1939"], "correct": "1945"},
    ],
    "medium": [
        {"question": "Who was the first woman to fly solo across the Atlantic?", 
         "answers": ["Amelia Earhart", "Harriet Tubman", "Eleanor Roosevelt", "Marie Curie"], "correct": "Amelia Earhart"},
    ],
    "hard": [
        {"question": "Which empire was known for its Roman baths?", 
         "answers": ["Roman Empire", "Ottoman Empire", "Mongol Empire", "Byzantine Empire"], "correct": "Roman Empire"},
    ]
}

# Function to start the trivia game with a selected category and difficulty
async def start_trivia_game(interaction, category, difficulty):
    trivia_dict = {
        "laws": laws_trivia,
        "geography": geography_trivia,
        "history": history_trivia
    }

    question_data = trivia_dict[category][difficulty][0]  # Select the first question from the chosen category and difficulty
    view = TriviaButtonView(question_data, category, difficulty)
    view.set_button_labels()  # Set the button labels to the answers

    await interaction.response.send_message(question_data['question'], view=view)  # Send the question with the answer buttons


# Slash Command to start the trivia game
@bot.tree.command(name="trivia", description="Start a trivia game based on category and difficulty")
async def trivia(interaction: discord.Interaction, category: str, difficulty: str):
    """Start a trivia game based on category and difficulty."""
    valid_categories = ['laws', 'geography', 'history']
    valid_difficulties = ['easy', 'medium', 'hard']

    if category not in valid_categories or difficulty not in valid_difficulties:
        await interaction.response.send_message("Invalid category or difficulty. Please use one of the following categories: laws, geography, history. And difficulty: easy, medium, hard.")
        return

    await start_trivia_game(interaction, category, difficulty)

async def fetch_time(interaction, city):
    url = f"http://api.timezonedb.com/v2.1/get-time-zone?key=Q5ZO00XFAX1A&format=json&by=zone&zone={city.value}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Si la respuesta es 4xx o 5xx, lanza un error
        
        data = response.json()  # Convertir la respuesta en JSON

        # 📌 Verificar si 'formatted' existe en la respuesta
        if 'formatted' in data:
            await interaction.response.send_message(f"La hora en {city.name} es {data['formatted']}")
        else:
            print("❌ Error: No se encontró 'formatted' en la respuesta")
            await interaction.response.send_message("No pude obtener la hora. Intenta de nuevo más tarde.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la solicitud: {e}")
        await interaction.response.send_message("Hubo un error al obtener la hora. Intenta más tarde.")

# America Time Command
@bot.tree.command(name="time_america", description="Get the time in major cities of the Americas.")
@app_commands.choices(
    city=[
        app_commands.Choice(name="New York", value="America/New_York"),
        app_commands.Choice(name="Los Angeles", value="America/Los_Angeles"),
        app_commands.Choice(name="Mexico City", value="America/Mexico_City"),
        app_commands.Choice(name="Rio de Janeiro", value="America/Sao_Paulo"),
        app_commands.Choice(name="São Paulo", value="America/Sao_Paulo"),
        app_commands.Choice(name="Buenos Aires", value="America/Argentina/Buenos_Aires"),
        app_commands.Choice(name="Toronto", value="America/Toronto"),
        app_commands.Choice(name="Lima", value="America/Lima"),
        app_commands.Choice(name="Bogotá", value="America/Bogota"),
        app_commands.Choice(name="Caracas", value="America/Caracas"),
    ]
)
async def time_america(interaction: discord.Interaction, city: app_commands.Choice[str]):
    await fetch_time(interaction, city)

# Europe Time Command
@bot.tree.command(name="time_europe", description="Get the time in major cities of Europe.")
@app_commands.choices(
    city=[
        app_commands.Choice(name="London", value="Europe/London"),
        app_commands.Choice(name="Paris", value="Europe/Paris"),
        app_commands.Choice(name="Berlin", value="Europe/Berlin"),
        app_commands.Choice(name="Rome", value="Europe/Rome"),
        app_commands.Choice(name="Madrid", value="Europe/Madrid"),
        app_commands.Choice(name="Moscow", value="Europe/Moscow"),
        app_commands.Choice(name="Athens", value="Europe/Athens"),
        app_commands.Choice(name="Stockholm", value="Europe/Stockholm"),
        app_commands.Choice(name="Vienna", value="Europe/Vienna"),
        app_commands.Choice(name="Oslo", value="Europe/Oslo"),
    ]
)
async def time_europe(interaction: discord.Interaction, city: app_commands.Choice[str]):
    await fetch_time(interaction, city)

# Asia Time Command
@bot.tree.command(name="time_asia", description="Get the time in major cities of Asia.")
@app_commands.choices(
    city=[
        app_commands.Choice(name="Tokyo", value="Asia/Tokyo"),
        app_commands.Choice(name="Singapore", value="Asia/Singapore"),
        app_commands.Choice(name="Beijing", value="Asia/Shanghai"),
        app_commands.Choice(name="Seoul", value="Asia/Seoul"),
        app_commands.Choice(name="Bangkok", value="Asia/Bangkok"),
        app_commands.Choice(name="Jakarta", value="Asia/Jakarta"),
        app_commands.Choice(name="Manila", value="Asia/Manila"),
        app_commands.Choice(name="Kuala Lumpur", value="Asia/Kuala_Lumpur"),
        app_commands.Choice(name="Hanoi", value="Asia/Ho_Chi_Minh"),
        app_commands.Choice(name="Dhaka", value="Asia/Dhaka"),
    ]
)
async def time_asia(interaction: discord.Interaction, city: app_commands.Choice[str]):
    await fetch_time(interaction, city)

# Africa Time Command
@bot.tree.command(name="time_africa", description="Get the time in major cities of Africa.")
@app_commands.choices(
    city=[
        app_commands.Choice(name="Cairo", value="Africa/Cairo"),
        app_commands.Choice(name="Lagos", value="Africa/Lagos"),
        app_commands.Choice(name="Nairobi", value="Africa/Nairobi"),
        app_commands.Choice(name="Cape Town", value="Africa/Johannesburg"),
        app_commands.Choice(name="Kinshasa", value="Africa/Kinshasa"),
        app_commands.Choice(name="Abuja", value="Africa/Abuja"),
        app_commands.Choice(name="Accra", value="Africa/Accra"),
        app_commands.Choice(name="Casablanca", value="Africa/Casablanca"),
        app_commands.Choice(name="Addis Ababa", value="Africa/Addis_Ababa"),
        app_commands.Choice(name="Dakar", value="Africa/Dakar"),
    ]
)
async def time_africa(interaction: discord.Interaction, city: app_commands.Choice[str]):
    await fetch_time(interaction, city)

# Oceania Time Command
@bot.tree.command(name="time_oceania", description="Get the time in major cities of Oceania.")
@app_commands.choices(
    city=[
        app_commands.Choice(name="Sydney", value="Australia/Sydney"),
        app_commands.Choice(name="Melbourne", value="Australia/Melbourne"),
        app_commands.Choice(name="Auckland", value="Pacific/Auckland"),
        app_commands.Choice(name="Wellington", value="Pacific/Auckland"),
        app_commands.Choice(name="Fiji", value="Pacific/Fiji"),
        app_commands.Choice(name="Port Moresby", value="Pacific/Port_Moresby"),
    ]
)
async def time_oceania(interaction: discord.Interaction, city: app_commands.Choice[str]):
    await fetch_time(interaction, city)

bot.run("TOKEN HERE")

