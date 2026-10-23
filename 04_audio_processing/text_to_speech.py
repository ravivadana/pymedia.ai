import os
from gtts import gTTS
import pygame


def text_to_speech(text, lang="en", filename="output.mp3"):
    """Converts input text to an MP3 file and plays it back."""
    print("Generating speech...")

    # 1. Convert text to speech
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(filename)

    # 2. Play the audio file using Pygame
    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    # Wait until the audio finishes playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    # Unload the file so it can be overwritten later
    pygame.mixer.music.unload()
    print("Done!")


# --- Usage Example ---
if __name__ == "__main__":
    # Triple quotes allow multi-line text blocks
    my_text = """Dear Respected GMR Garu,

Pranams.

Returning to GMRIT for our Silver Jubilee Reunion, twenty-five years after we completed our B.Tech as its first batch, was a deeply emotional experience. Nearly a hundred of us travelled from different parts of the world to return to where our journeys began and witness the extraordinary transformation of GMRIT from a young institution into the Deemed-to-be University it is today.

Meeting you made this milestone even more meaningful.

Thank you, Sir, for taking nearly an hour from your demanding schedule to interact with us, share your life’s experiences, speak about the values that shaped the GMR Group, and patiently answer our questions. Your acknowledgement of the trust that our parents and the very first batch placed in GMRIT touched each one of us.

When you asked how many among us had become entrepreneurs, were continuing family businesses, serving as professionals, or were homemakers, you reminded us that every path in life deserves equal respect. In that simple interaction, each one of us felt recognised—not for our titles, but for the lives we have built with purpose and dignity.

As you spoke about the Seven Core Values of GMR—
Humility
Entrepreneurship
Teamwork & Relationships
Deliver the Promise
Learning & Inner Excellence
Social Responsibility
Respect for the Individual

—we realised something profound:

We had experienced those values long before we ever knew their names.

We still remember your visits to our hostel, personally checking even the washrooms to ensure cleanliness and proper facilities. We also remember the concerns during our early days about insects and insect bites, and how you ensured that expert medical guidance and reassurance were immediately provided.

Looking back today, those may have seemed like small gestures, but they reflected extraordinary leadership. You led not only through vision, but through humility, compassion, and attention to every detail that mattered to your students. Those experiences became our first lessons in leadership.

Your reflections on humility left perhaps the deepest impact. The distinction you drew between self-confidence and ego was profound. You reminded us that confidence enables success, but humility sustains it and earns lasting respect.

Equally inspiring was your message on the importance of having a burning desire to achieve our goals. You reminded us that talent and opportunity alone are never enough—it is unwavering passion, perseverance, and commitment that transform dreams into reality. Those words rekindled aspirations in many of us, irrespective of where we are in our journeys.

We were equally touched by your emphasis on caring for our emotional and inner well-being alongside our physical health. Your encouragement to embrace practices such as Yoga, Meditation, Art of Living, Brahma Kumaris, or any path that nurtures inner peace reminded us that true success is measured not only by what we achieve, but also by the peace and balance we cultivate within ourselves.

It was equally emotional for us to felicitate our beloved teachers and thank them for the knowledge, discipline, and values that continue to guide us throughout our lives.

Sir, airports, power plants, highways, and institutions stand as remarkable symbols of your vision and leadership. Yet, for us, your greatest legacy is something even more enduring—the thousands of lives transformed because you believed that world-class education could flourish in Rajam. We are honoured to have been the first chapter of that remarkable journey.

We are also deeply grateful for your gracious invitation to visit the Vizag Airport after August 2 and for your generous offer to personally arrange the visit. It is another reflection of your continued affection for your students, and we eagerly look forward to that opportunity.

As our Silver Jubilee celebrations came to a close, one thought remained with all of us: our journey had come full circle. You gave us an institution that prepared us for successful careers. At this reunion, you reminded us that the true purpose of education is to become better human beings—grounded in humility, driven by purpose, and committed to lifelong learning.

Thank you, Sir, for your vision, your guidance, your blessings, and your unwavering faith in your students. We will carry your words with us for the rest of our lives and strive to uphold the values you so passionately shared.

With our deepest respect, admiration, and gratitude,

The First B.Tech Batch of GMRIT  
1997–2001"""

    text_to_speech(my_text)