from feedgen.feed import FeedGenerator
import json
from datetime import datetime, timezone
import os
from urllib.parse import urlparse

def create_podcast_feed(talks_file: str, output_file: str):
    # Load the talks data
    with open(talks_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create feed generator
    fg = FeedGenerator()
    fg.load_extension('podcast')
    
    # Set feed metadata
    fg.title('Migraine World Summit 2025')
    fg.description('Expert interviews and discussions from the Migraine World Summit 2025')
    fg.link(href='https://migraineworldsummit.com/summit/2025-summit/')
    fg.language('en')
    fg.pubDate(datetime.now(timezone.utc))
    fg.image(data['logo_url'])
    
    # Add each talk as an episode
    for talk in data['talks']:
        fe = fg.add_entry()
        
        # Set episode title and description
        fe.title(talk['title'])
        description = f"Presenter: {talk['presenter_name']}\n"
        if talk['presenter_role']:
            description += f"Role: {talk['presenter_role']}\n"
        if talk['institution']:
            description += f"Institution: {talk['institution']}\n"
        if talk['key_questions']:
            description += "\nKey Questions:\n" + "\n".join(f"- {q}" for q in talk['key_questions'])
        fe.description(description)
        
        # Add presenter image
        if talk['presenter_image']:
            fe.podcast.itunes_image(talk['presenter_image'])
        
        # Add audio file
        if talk['media_links']['audio_full']:
            fe.enclosure(talk['media_links']['audio_full'], 0, 'audio/mpeg')
        
        # Add publication date (use current date if not available)
        fe.pubDate(datetime.now(timezone.utc))
        
        # Add GUID (use audio URL or title)
        guid = talk['media_links']['audio_full'] or talk['title']
        fe.guid(guid)
        
        # Add duration if available (you might need to extract this from the audio file)
        # fe.podcast.itunes_duration('01:00:00')
    
    # Generate the feed
    fg.rss_file(output_file)
    print(f"Podcast feed generated: {output_file}")

def main():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define input and output paths
    talks_file = os.path.join(script_dir, 'talks.json')
    output_file = os.path.join(script_dir, 'mws2025_podcast.xml')
    
    # Create the podcast feed
    create_podcast_feed(talks_file, output_file)

if __name__ == "__main__":
    main() 