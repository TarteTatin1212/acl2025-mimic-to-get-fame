import random
import string
import re
from typing import List, Tuple
import spacy
import requests
import numpy as np
from Levenshtein import distance as levenshtein_distance
import nltk
from nltk.corpus import words as nltk_words


# Ensure NLTK data is downloaded
nltk.download('words')

# Load spaCy model
nlp = spacy.load("en_core_web_sm")


# Define the word list for perturbations
word_list = nltk_words.words()


# Contraction dictionary
CONTRACTIONS = {
    "are not": "aren't",
    "cannot": "can't",
    "could not": "couldn't",
    "did not": "didn't",
    "does not": "doesn't",
    "do not": "don't",
    "had not": "hadn't",
    "has not": "hasn't",
    "have not": "haven't",
    "he is": "he's",
    "I am": "I'm",
    "is not": "isn't",
    "it is": "it's",
    "she is": "she's",
    "that is": "that's",
    "they are": "they're",
    "was not": "wasn't",
    "we are": "we're",
    "were not": "weren't",
    "will not": "won't",
    "would not": "wouldn't",
    "you are": "you're"
}



class CharacterLevelNoise:
    """
    A class to apply character-level noises to text, including swapping, substitution, deletion, and insertion.
    """

    # Define a dictionary of nearby keys on a QWERTY keyboard
    NEARBY_KEYS = {
        'q': 'was', 'w': 'qeasd', 'e': 'wrsdf', 'r': 'etdfg', 't': 'ryfgh', 'y': 'tughj', 'u': 'yihjk',
        'i': 'uojkl', 'o': 'ipkl', 'p': 'ol',
        'a': 'qwsxz', 's': 'qweadzx', 'd': 'werfcxs', 'f': 'ertgvcd', 'g': 'rtyhbvf', 'h': 'tyujnbg',
        'j': 'yuikmnh', 'k': 'uiolmj', 'l': 'opk',
        'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'
    }

    def __init__(self, swap_prob=0.05, substitution_prob=0.05, deletion_prob=0.02, insertion_prob=0.02, enabled_transforms=None):
        """
        Initializes the CharacterLevelNoise class with specified probabilities and enabled transformations.

        :param swap_prob: Probability of swapping characters.
        :param substitution_prob: Probability of substituting characters.
        :param deletion_prob: Probability of deleting characters.
        :param insertion_prob: Probability of inserting characters.
        :param enabled_transforms: List of transformations to apply. Possible values: 'swap', 'substitute', 'delete', 'insert'.
        """
        self.swap_prob = swap_prob
        self.substitution_prob = substitution_prob
        self.deletion_prob = deletion_prob
        self.insertion_prob = insertion_prob
        self.enabled_transforms = enabled_transforms if enabled_transforms else ['swap', 'substitute', 'delete', 'insert']

    def swap_characters(self, word):
        """
        Swaps two adjacent characters in the word.

        :param word: The word to modify.
        :return: Word with two adjacent characters swapped.
        """
        if len(word) <= 1:
            return word
        i = random.randint(0, len(word) - 2)
        chars = list(word)
        chars[i], chars[i+1] = chars[i+1], chars[i]
        return ''.join(chars)

    def substitute_characters(self, word):
        """
        Substitutes a character with a nearby key on the QWERTY keyboard or a random character.

        :param word: The word to modify.
        :return: Word with a substituted character.
        """
        if not word:
            return word
        i = random.randint(0, len(word) - 1)
        chars = list(word)
        char_lower = chars[i].lower()
        if char_lower in self.NEARBY_KEYS:
            substitute_options = self.NEARBY_KEYS[char_lower]
            substitute_char = random.choice(substitute_options)
            # Preserve original case
            substitute_char = substitute_char.upper() if chars[i].isupper() else substitute_char
            chars[i] = substitute_char
        else:
            # Substitute with a random lowercase letter
            substitute_char = random.choice(string.ascii_lowercase)
            substitute_char = substitute_char.upper() if chars[i].isupper() else substitute_char
            chars[i] = substitute_char
        return ''.join(chars)

    def delete_character(self, word):
        """
        Deletes a character from the word.

        :param word: The word to modify.
        :return: Word with one character deleted.
        """
        if len(word) <= 1:
            return word
        i = random.randint(0, len(word) - 1)
        return word[:i] + word[i+1:]

    def insert_character(self, word):
        """
        Inserts a random character into the word.
        :param word: The word to modify.
        :return: Word with an inserted character.
        """
        i = random.randint(0, len(word))
        char = random.choice(string.ascii_lowercase)
        # Optionally, insert uppercase letters or symbols
        if random.random() < 0.1:  # 10% chance to insert uppercase
            char = char.upper()
        return word[:i] + char + word[i:]

    def apply_noise_to_word(self, word):
        """
        Applies a random transformation to the word based on enabled transformations and their probabilities.
        :param word: The word to modify.
        :return: Word with applied noise.
        """
        transforms = []
        if 'swap' in self.enabled_transforms and random.random() < self.swap_prob:
            transforms.append(self.swap_characters)
        if 'substitute' in self.enabled_transforms and random.random() < self.substitution_prob:
            transforms.append(self.substitute_characters)
        if 'delete' in self.enabled_transforms and random.random() < self.deletion_prob:
            transforms.append(self.delete_character)
        if 'insert' in self.enabled_transforms and random.random() < self.insertion_prob:
            transforms.append(self.insert_character)

        for transform in transforms:
            word = transform(word)
        return word

    def apply_noise_to_text(self, text):
        """
        Applies character-level noise to each word in the text based on specified probabilities.

        :param text: The original text.
        :return: Text with character-level noises applied.
        """
        def noise_function(match):
            word = match.group(0)
            noisy_word = self.apply_noise_to_word(word)
            return noisy_word

        # Use regex to split the text into words while preserving punctuation
        pattern = r'\b\w+\b'
        noisy_text = re.sub(pattern, noise_function, text)
        return noisy_text

class CharacterNoiseApplier(CharacterLevelNoise):
    def __init__(self, swap_prob=0.05, substitution_prob=0.05, deletion_prob=0.02, insertion_prob=0.02, enabled_transforms=None):
        super().__init__(swap_prob, substitution_prob, deletion_prob, insertion_prob, enabled_transforms)

    def split_transcript(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Split the transcript into speaker annotations, actions, and spoken content.

        :param text: The input transcript text
        :return: A list of tuples containing (speaker, action, content)
        """
        lines = text.split('\n')
        transcript_parts = []

        for line in lines:
            speaker_match = re.match(r'^>>(.+?):\s*(.*)', line.strip())
            action_match = re.match(r'^\*(.*?)\*', line.strip())

            if speaker_match:
                speaker, content = speaker_match.groups()
                # Extract any inline actions
                content_parts = re.split(r'(\*.*?\*)', content)
                for i, part in enumerate(content_parts):
                    if i % 2 == 0:  # Even indices are spoken content
                        if part.strip():
                            transcript_parts.append((speaker, '', part.strip()))
                    else:  # Odd indices are actions
                        transcript_parts.append((speaker, part, ''))
            elif action_match:
                action = action_match.group(1)
                transcript_parts.append(('', action, ''))
            else:
                # If there's no speaker annotation or action, treat the whole line as content
                transcript_parts.append(('', '', line))

        return transcript_parts


    def apply_noise_to_transcript(self, text: str) -> str:
        """
        Apply character-level noise to the transcript while preserving formatting, speaker annotations, and actions.

        :param text: The original transcript text
        :return: The transcript with character-level noise applied
        """
        transcript_parts = self.split_transcript(text)
        noisy_transcript = []

        for speaker, action, content in transcript_parts:
            if content:
                noisy_content = self.apply_noise_to_text(content)
                if speaker:
                    noisy_transcript.append(f">>{speaker}: {noisy_content}")
                else:
                    noisy_transcript.append(noisy_content)
            elif action:
                if speaker:
                    noisy_transcript.append(f">>{speaker}: *{action}*")
                else:
                    noisy_transcript.append(f"*{action}*")
            else:
                noisy_transcript.append('')  # Preserve empty lines

        return '\n'.join(noisy_transcript)


def test_character_noise():
    original_transcript = """
>>Robotics Engineer: Let's break this down further. From a technical standpoint—
*Phone rings loudly*
>>Mechanical Engineer: Oh sorry about that! *quickly silences phone* Please continue.
>>Robotics Engineer: No problem! As I was saying—from a technical standpoint—integrating these sensory feedback mechanisms into robotic systems is akin to giving them a sixth sense. \nFor example, tactile sensors enable robots to handle fragile objects delicately while lidar and radar allow for precise navigation even in cluttered or dynamic environments. This multi-sensory approach ensures that robots can adapt and respond effectively to real-world challenges.
>>Mechanical Engineer: So, let's break this down. Series elastic actuation (SEA) is a fascinating advancement in actuator technology. By introducing intentional elasticity between the motor and the load, we achieve robust force control and improved safety during interactions with the environment. This is particularly beneficial for robots working alongside humans or handling delicate tasks. Right?
>>Artificial Intelligence Specialist: Absolutely. Considering SEA's advancements, integrating machine learning algorithms can significantly enhance these actuators' adaptability and efficiency. By processing real-time data from sensors, we can enable robots to adjust their force control dynamically, ensuring both safety and precision during interactions.
>>Robotics Engineer: [Phone buzzes] Oh, sorry about that—let me just silence my phone... Okay, where was I? Right, considering power sources for these advanced robotic systems, we need to evaluate the trade-offs between using batteries, generators, and tethered supplies. Batteries offer portability but can be heavy and have limited life cycles. Generators provide continuous power but add mechanical complexity and weight. Tethered supplies eliminate weight concerns but restrict mobility due to cable management issues.
"""

    noise_applier = CharacterNoiseApplier(
        swap_prob=0.05,
        substitution_prob=0.05,
        deletion_prob=0.02,
        insertion_prob=0.02,
        enabled_transforms=['swap', 'substitute', 'delete', 'insert']
    )

    noisy_transcript = noise_applier.apply_noise_to_transcript(original_transcript)
    print("Original Transcript:")
    print(original_transcript)
    print("\nNoisy Transcript:")
    print(noisy_transcript)


class WordLevelNoise:
    """
    A class to apply word-level noises to text, including contractions addition,
    phonetic substitutions, named entity replacements, text perturbations,
    gender bias perturbations, and word swapping.
    """


    def __init__(self, noise_types=None, noise_level=0.3):
        """
        Initialize the WordLevelNoise class with specified noise types and noise level.


        :param noise_types: List of noise types to apply.
                            Options: "contractions", "phonetic", "named_entity",
                                     "gender_bias", "add_perturbations", "swap_perturbations"
        :param noise_level: Probability of applying each noise type.
        """
        if noise_types is None:
            noise_types = [
                "contractions",
                "phonetic",
                "named_entity",
                "gender_bias",
                "add_perturbations",
                "swap_perturbations"
            ]
        self.noise_types = noise_types
        self.noise_level = noise_level
        self.contraction_patterns = self._compile_contraction_patterns()


    def _compile_contraction_patterns(self):
        """
        Compile regex patterns for contractions to ensure accurate replacements.


        :return: Dictionary with regex patterns as keys and contractions as values.
        """
        patterns = {}
        for phrase, contraction in CONTRACTIONS.items():
            # Use word boundaries to ensure exact matches
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            patterns[pattern] = contraction
        return patterns


    def add_contractions(self, text):
        """
        Replaces formal phrases with contractions based on the specified probability.


        :param text: The original text.
        :return: Text with contractions added.
        """
        def replace(match):
            original = match.group(0)
            contraction = self.contraction_patterns[match.re].lower()
            # Preserve the original casing
            if original.isupper():
                return contraction.upper()
            elif original[0].isupper():
                return contraction.capitalize()
            else:
                return contraction


        for pattern, contraction in self.contraction_patterns.items():
            if random.random() < self.noise_level:
                text = pattern.sub(replace, text)
        return text


    def get_phonetically_similar_words(self, word):
        """
        Fetches phonetically similar words using the Datamuse API.


        :param word: The original word.
        :return: List of phonetically similar words.
        """
        try:
            response = requests.get(f"https://api.datamuse.com/words?sl={word}&max=10")
            return [item["word"] for item in response.json()]
        except requests.RequestException:
            return []


    def cosine_similarity(self, vec1, vec2):
        """
        Calculates cosine similarity between two vectors.


        :param vec1: First vector.
        :param vec2: Second vector.
        :return: Cosine similarity score.
        """
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


    def get_most_dissimilar_word(self, original_word, similar_words):
        """
        Selects the most semantically dissimilar word from a list of similar-sounding words.


        :param original_word: The original word.
        :param similar_words: List of phonetically similar words.
        :return: The most semantically dissimilar word.
        """
        original_vector = nlp(original_word).vector
        valid_words = [word for word in similar_words if word in nlp.vocab]
        if valid_words:
            similarities = [self.cosine_similarity(original_vector, nlp(word).vector) for word in valid_words]
            return valid_words[np.argmin(similarities)]
        else:
            # Fallback to selecting a word with maximum Levenshtein distance
            distances = [levenshtein_distance(original_word, word) for word in similar_words]
            if distances:
                return similar_words[np.argmax(distances)]
            else:
                return original_word


    def replace_with_phonetically_similar(self, text):
        """
        Replaces words with phonetically similar but semantically different words.


        :param text: The original text.
        :return: Text with phonetically similar word replacements.
        """
        doc = nlp(text)
        words = [token.text for token in doc]


        for i, token in enumerate(doc):
            if random.random() < self.noise_level and token.pos_ in ["NOUN", "VERB", "ADJ", "ADV"]:
                similar_words = self.get_phonetically_similar_words(token.text)
                if similar_words:
                    dissimilar_word = self.get_most_dissimilar_word(token.text, similar_words)
                    # Preserve the original casing
                    if token.text.isupper():
                        dissimilar_word = dissimilar_word.upper()
                    elif token.text[0].isupper():
                        dissimilar_word = dissimilar_word.capitalize()
                    words[i] = dissimilar_word

        return " ".join(words)


    def replace_named_entities(self, text):
        """
        Replaces named entities with other entities of the same type.


        :param text: The original text.
        :return: Text with named entities replaced.
        """
        doc = nlp(text)
        words = [token.text for token in doc]


        entities = [(ent.start, ent.end, ent.label_) for ent in doc.ents]


        for start, end, label in entities:
            if random.random() < self.noise_level:
                replacement = self._get_entity_replacement(label)
                if replacement:
                    words[start:end] = [replacement] * (end - start)


        return " ".join(words)


    def _get_entity_replacement(self, label):
        """
        Provides a replacement entity based on the entity label.


        :param label: The spaCy entity label.
        :return: A replacement entity string.
        """
        replacement_dict = {
            "PERSON": ["John", "Emma", "Michael", "Sophia", "David", "Olivia"],
            "ORG": ["Google", "Microsoft", "Apple", "Amazon", "Facebook"],
            "GPE": ["New York", "London", "Paris", "Tokyo", "Berlin"],
            "LOC": ["Mount Everest", "Sahara Desert", "Great Barrier Reef"],
            "DATE": ["January 1st", "March 15th", "July 4th"],
            "TIME": ["10:00 AM", "2:30 PM", "5:45 PM"],
            "MONEY": ["$1000", "$500", "$2500"],
            "PRODUCT": ["iPhone", "Galaxy", "Pixel"],
            "EVENT": ["Olympics", "World Cup", "Super Bowl"]
            # Add more entity types and replacements as needed
        }
        return random.choice(replacement_dict.get(label, []))


    def add_text_perturbations(self, text):
        """
        Adds random words into the text to simulate noise.


        :param text: The original text.
        :return: Text with added perturbations.
        """
        words = text.split()
        perturbed_words = words.copy()


        num_insertions = int(len(words) * self.noise_level)
        for _ in range(num_insertions):
            insert_position = random.randint(0, len(perturbed_words))
            num_words = random.randint(1, 3)
            inserted_words = [random.choice(word_list) for _ in range(num_words)]
            perturbed_words[insert_position:insert_position] = inserted_words


        return " ".join(perturbed_words)


    def gender_bias_perturbations(self, text):
        """
        Swaps gender-specific words to test model robustness against gender bias.


        :param text: The original text.
        :return: Text with gender bias perturbations.
        """
        gender_pairs = {
            "he": "she", "she": "he",
            "him": "her", "her": "him",
            "his": "her", "hers": "his",
            "himself": "herself", "herself": "himself",
            "man": "woman", "woman": "man",
            "boy": "girl", "girl": "boy",
            "father": "mother", "mother": "father",
            "son": "daughter", "daughter": "son",
            "husband": "wife", "wife": "husband",
            "brother": "sister", "sister": "brother",
            "uncle": "aunt", "aunt": "uncle",
            "nephew": "niece", "niece": "nephew",
            "father-in-law": "mother-in-law", "mother-in-law": "father-in-law",
            "son-in-law": "daughter-in-law", "daughter-in-law": "son-in-law",
            "stepfather": "stepmother", "stepmother": "stepfather",
            "godfather": "godmother", "godmother": "godfather",
            "father": "mother", "mother": "father",
            "boyfriend": "girlfriend", "girlfriend": "boyfriend",
            'Mr.': 'Ms.', 'Ms.': 'Mr.',
            'actor': 'actress', 'actress': 'actor',
        }


        words = text.split()
        for i, word in enumerate(words):
            lower_word = word.lower()
            if lower_word in gender_pairs and random.random() < self.noise_level:
                replacement = gender_pairs[lower_word]
                # Preserve original casing
                if word.isupper():
                    replacement = replacement.upper()
                elif word[0].isupper():
                    replacement = replacement.capitalize()
                words[i] = replacement
        return " ".join(words)


    def swap_text_perturbations(self, text):
        """
        Randomly swaps two words in the text to simulate noise.


        :param text: The original text.
        :return: Text with words swapped.
        """
        words = text.split()
        swapped_words = words.copy()


        num_swaps = int(len(words) * self.noise_level)
        for _ in range(num_swaps):
            if len(swapped_words) < 2:
                break
            i, j = random.sample(range(len(swapped_words)), 2)
            swapped_words[i], swapped_words[j] = swapped_words[j], swapped_words[i]


        return " ".join(swapped_words)


    def apply_noise_to_word(self, word, noise_type):
        """
        Apply a specific word-level noise to a single word.


        :param word: The original word.
        :param noise_type: The type of noise to apply.
        :return: The word with applied noise.
        """
        if noise_type == "contractions":
            return self.add_contractions(word)
        elif noise_type == "phonetic":
            return self.replace_with_phonetically_similar(word)
        elif noise_type == "named_entity":
            return self.replace_named_entities(word)
        elif noise_type == "gender_bias":
            return self.gender_bias_perturbations(word)
        elif noise_type == "add_perturbations":
            return self.add_text_perturbations(word)
        elif noise_type == "swap_perturbations":
            return self.swap_text_perturbations(word)
        else:
            return word


    def apply_noise_to_text(self, text):
        """
        Apply selected word-level noises to the entire text.


        :param text: The original text.
        :return: Text with word-level noises applied.
        """
        for noise_type in self.noise_types:
            if noise_type == "contractions":
                text = self.add_contractions(text)
            elif noise_type == "phonetic":
                text = self.replace_with_phonetically_similar(text)
            elif noise_type == "named_entity":
                text = self.replace_named_entities(text)
            elif noise_type == "gender_bias":
                text = self.gender_bias_perturbations(text)
            elif noise_type == "add_perturbations":
                text = self.add_text_perturbations(text)
            elif noise_type == "swap_perturbations":
                text = self.swap_text_perturbations(text)
        return text


class WordNoiseApplier(WordLevelNoise):
    def __init__(self, noise_types=None, noise_level=0.3):
        super().__init__(noise_types, noise_level)

    def split_transcript(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Split the transcript into speaker annotations, actions, and spoken content.

        :param text: The input transcript text
        :return: A list of tuples containing (speaker, action, content)
        """
        lines = text.split('\n')
        transcript_parts = []

        for line in lines:
            speaker_match = re.match(r'^>>(.+?):\s*(.*)', line.strip())
            action_match = re.match(r'^\*(.*?)\*', line.strip())

            if speaker_match:
                speaker, content = speaker_match.groups()
                # Extract any inline actions
                content_parts = re.split(r'(\*.*?\*)', content)
                for i, part in enumerate(content_parts):
                    if i % 2 == 0:  # Even indices are spoken content
                        if part.strip():
                            transcript_parts.append((speaker, '', part.strip()))
                    else:  # Odd indices are actions
                        transcript_parts.append((speaker, part, ''))
            elif action_match:
                action = action_match.group(1)
                transcript_parts.append(('', action, ''))
            else:
                # If there's no speaker annotation or action, treat the whole line as content
                transcript_parts.append(('', '', line))

        return transcript_parts


    def apply_noise_to_transcript(self, text: str) -> str:
        """
        Apply noise to the transcript while preserving formatting, speaker annotations, and actions.

        :param text: The original transcript text
        :return: The transcript with noise applied
        """
        transcript_parts = self.split_transcript(text)
        noisy_transcript = []

        for speaker, action, content in transcript_parts:
            if content:
                noisy_content = self.apply_noise_to_text(content)
                if speaker:
                    noisy_transcript.append(f">>{speaker}: {noisy_content}")
                else:
                    noisy_transcript.append(noisy_content)
            elif action:
                if speaker:
                    noisy_transcript.append(f">>{speaker}: *{action}*")
                else:
                    noisy_transcript.append(f"*{action}*")
            else:
                noisy_transcript.append('')  # Preserve empty lines

        return '\n'.join(noisy_transcript)


def test_word_noise():
    original_transcript = """
>>Robotics Engineer: Let's break this down further.\n From a technical standpoint—
*Phone rings loudly*
>>Mechanical Engineer: Oh sorry about that! *quickly silences phone* Please continue.
>>Robotics Engineer: No problem! As I was saying—from a technical standpoint—integrating these sensory feedback mechanisms into robotic systems is akin to giving them a sixth sense. For example, tactile sensors enable robots to handle fragile objects delicately while lidar and radar allow for precise navigation even in cluttered or dynamic environments. This multi-sensory approach ensures that robots can adapt and respond effectively to real-world challenges.
>>Mechanical Engineer: So, let's break this down. Series elastic actuation (SEA) is a fascinating advancement in actuator technology. By introducing intentional elasticity between the motor and the load, we achieve robust force control and improved safety during interactions with the environment. This is particularly beneficial for robots working alongside humans or handling delicate tasks. Right?
>>Artificial Intelligence Specialist: Absolutely. Considering SEA's advancements, integrating machine learning algorithms can significantly enhance these actuators' adaptability and efficiency. By processing real-time data from sensors, we can enable robots to adjust their force control dynamically, ensuring both safety and precision during interactions.
>>Robotics Engineer: [Phone buzzes] Oh, sorry about that—let me just silence my phone... Okay, where was I? Right, considering power sources for these advanced robotic systems, we need to evaluate the trade-offs between using batteries, generators, and tethered supplies. Batteries offer portability but can be heavy and have limited life cycles. Generators provide continuous power but add mechanical complexity and weight. Tethered supplies eliminate weight concerns but restrict mobility due to cable management issues.
"""

    noise_applier = WordNoiseApplier(
        noise_types=["contractions", "phonetic", "gender_bias", "add_perturbations", "swap_perturbations"],
        noise_level=0.1  # Adjust based on desired noise intensity
    )

    noisy_transcript = noise_applier.apply_noise_to_transcript(original_transcript)
    print("Original Transcript:")
    print(original_transcript)
    print("\nNoisy Transcript:")
    print(noisy_transcript)


class SentenceNoiseApplier:
    def __init__(self, noise_types: List[str] = None, noise_level: float = 0.3):
        self.noise_types = noise_types or ["word_order_shuffling", "drop_first_last"]
        self.noise_level = noise_level


    def split_transcript(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Split the transcript into speaker annotations, actions, and spoken content.
       
        :param text: The input transcript text
        :return: A list of tuples containing (speaker, action, content)
        """
        lines = text.split('\n')
        transcript_parts = []
       
        for line in lines:
            speaker_match = re.match(r'^>>(.+?):\s*(.*)', line.strip())
            action_match = re.match(r'^\*(.*?)\*', line.strip())
           
            if speaker_match:
                speaker, content = speaker_match.groups()
                # Extract any inline actions
                content_parts = re.split(r'(\*.*?\*)', content)
                for i, part in enumerate(content_parts):
                    if i % 2 == 0:  # Even indices are spoken content
                        if part.strip():
                            transcript_parts.append((speaker, '', part.strip()))
                    else:  # Odd indices are actions
                        transcript_parts.append((speaker, part, ''))
            elif action_match:
                action = action_match.group(1)
                transcript_parts.append(('', action, ''))
            else:
                # If there's no speaker annotation or action, treat the whole line as content
                transcript_parts.append(('', '', line))

        return transcript_parts


    def apply_noise_to_transcript(self, text: str) -> str:
        """
        Apply sentence-level noise to the transcript while preserving formatting, speaker annotations, and actions.

        :param text: The original transcript text
        :return: The transcript with sentence-level noise applied
        """
        transcript_parts = self.split_transcript(text)
        noisy_transcript = []

        for speaker, action, content in transcript_parts:
            if content:
                noisy_content = self._apply_noise_to_content(content)
                if speaker:
                    noisy_transcript.append(f">>{speaker}: {noisy_content}")
                else:
                    noisy_transcript.append(noisy_content)
            elif action:
                if speaker:
                    noisy_transcript.append(f">>{speaker}: *{action}*")
                else:
                    noisy_transcript.append(f"*{action}*")
            else:
                noisy_transcript.append('')  # Preserve empty lines

        return '\n'.join(noisy_transcript)


    def _apply_noise_to_content(self, content: str) -> str:
        # Split the content into sentences
        sentences = re.split(r'(?<=[.!?])\s+', content)
        noised_sentences = []


        for sentence in sentences:
            if random.random() < self.noise_level:
                for noise_type in self.noise_types:
                    if noise_type == "word_order_shuffling":
                        sentence = self._word_order_shuffling(sentence)
                    elif noise_type == "drop_first_last":
                        sentence = self._drop_first_last_perturbations(sentence)
            noised_sentences.append(sentence)


        return ' '.join(noised_sentences)


    def _word_order_shuffling(self, sentence: str) -> str:
        # Preserve leading/trailing whitespace and punctuation
        leading_space, content, trailing_punct = self._split_sentence(sentence)
        words = content.split()
        if len(words) > 1:
            shuffled_words = words[:]
            while shuffled_words == words:
                random.shuffle(shuffled_words)
            return leading_space + ' '.join(shuffled_words) + trailing_punct
        return sentence


    def _drop_first_last_perturbations(self, sentence: str) -> str:
        leading_space, content, trailing_punct = self._split_sentence(sentence)
        words = content.split()
        if len(words) > 2:
            if random.choice([True, False]):
                words = words[1:]  # Drop first
            else:
                words = words[:-1]  # Drop last
        return leading_space + ' '.join(words) + trailing_punct


    def _split_sentence(self, sentence: str) -> Tuple[str, str, str]:
        # Split sentence into leading whitespace, content, and trailing punctuation
        match = re.match(r'^(\s*)(.+?)(\s*[.!?]*)$', sentence)
        if match:
            return match.groups()
        return '', sentence, ''


def test_sentence_noise():
    original_transcript = """
>>Robotics Engineer: Let's break this down further. From a technical standpoint—
*Phone rings loudly*
>>Mechanical Engineer: Oh sorry about that! *quickly silences phone* Please continue.
>>Robotics Engineer: No problem! As I was saying—from a technical standpoint—integrating these sensory feedback mechanisms into robotic systems is akin to giving them a sixth sense. For example, tactile sensors enable robots to handle fragile objects delicately while lidar and radar allow for precise navigation even in cluttered or dynamic environments. This multi-sensory approach ensures that robots can adapt and respond effectively to real-world challenges.
>>Mechanical Engineer: So, let's break this down. Series elastic actuation (SEA) is a fascinating advancement in actuator technology. \nBy introducing intentional elasticity between the motor and the load, we achieve robust force control and improved safety during interactions with the environment. This is particularly beneficial for robots working alongside humans or handling delicate tasks. Right?
>>Artificial Intelligence Specialist: Absolutely. Considering SEA's advancements, integrating machine learning algorithms can significantly enhance these actuators' adaptability and efficiency. By processing real-time data from sensors, we can enable robots to adjust their force control dynamically, ensuring both safety and precision during interactions.
>>Robotics Engineer: [Phone buzzes] Oh, sorry about that—let me just silence my phone... Okay, where was I? Right, considering power sources for these advanced robotic systems, we need to evaluate the trade-offs between using batteries, generators, and tethered supplies. Batteries offer portability but can be heavy and have limited life cycles. Generators provide continuous power but add mechanical complexity and weight. Tethered supplies eliminate weight concerns but restrict mobility due to cable management issues.
"""

    noise_applier = SentenceNoiseApplier(
        noise_types=["word_order_shuffling", "drop_first_last"],
        noise_level=0.5  # 50% probability to apply each noise type
    )

    noisy_transcript = noise_applier.apply_noise_to_transcript(original_transcript)
    print("Original Transcript:")
    print(original_transcript)
    print("\nNoisy Transcript:")
    print(noisy_transcript)



if __name__ == "__main__":
    print(f"="*120)
    print("**Character-level Noises**:\n")
    test_character_noise()
    print(f"="*120)
    print("**Word-level Noises**:\n")
    test_word_noise()
    print(f"="*120)
    print("**Sentence-level Noises**:\n")
    test_sentence_noise()

