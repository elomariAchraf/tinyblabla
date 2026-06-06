"""Integration tests: multiple components working together on realistic inputs."""
from tinyblabla.language import detect_language
from tinyblabla.parser import parse_suggestions, stream_parse

ENGLISH_INPUT = [
    # Syntaxe tordue / ordre des mots bizarre
    "The cake by the dog was eaten happily the garden in.",
    "Yesterday I will go to the store that I went tomorrow.",
    "She not never doesn't want nothing from nobody.",  # double/triple négation
    "More faster than the cheetah, the snail ran.",
    "Him and me went to the store and buyed some things.",

    # Sens incohérent / contradictions logiques
    "The silence was so loud it made everyone go deaf from the quiet.",
    "I always never do anything sometimes.",
    "The invisible pink elephant sat visibly in the empty full room.",
    "He was completely partially finished with his task.",
    "She arrived before she left, but after she came back.",

    # Phrases trop longues / mal structurées
    "The man which his dog that the cat scratched which belonged to the woman who lived in the house that Jack built barked.",
    "I think that I know that you know that she knows that we know nothing.",

    # Temps et conjugaisons mélangés
    "Tomorrow I was going to the park when I will have seen him yesterday.",
    "She have went to school and will had learned everything.",
]

FRENCH_INPUT = [
    # Ordre des mots disloqué
    "Demain hier soir j'irai je suis allé au marché ensemble seul.",
    "Le chat la souris mange toujours depuis jamais.",
    "Moi j'ai pas rien dit à personne jamais nulle part.",  # négations empilées

    # Contradictions logiques / sens absurde
    "Le silence criait si fort que tout le monde s'endormit en se réveillant.",
    "Il est arrivé avant de partir et reparti après être resté.",
    "La lumière noire illuminait obscurément la pièce vide pleine de monde.",
    "Je suis complètement à moitié sûr de ne pas tout à fait savoir.",
    "Toujours je ne fais jamais parfois rien de temps en temps.",

    # Temps et modes mélangés
    "Hier je mangerai ce que demain j'ai mangé la semaine prochaine.",
    "Si j'aurais su, j'aurais pas venu mais j'irai quand même hier.",
    "Elle sera venue quand il ira parti après qu'il viendra.",

    # Syntaxe cassée / anacoluthes
    "Mon voisin que sa femme elle est partie il habite depuis longtemps là.",
    "Les enfants que leurs parents leur ont dit de pas faire ça ils le font.",
    "C'est lui que je lui ai dit que sa mère elle m'a parlé de lui.",
]

# Realistic model outputs as Mistral would produce them.
ENGLISH_OUTPUT = (
    "1. This sentence contains grammatical errors.\n"
    "2. There are several mistakes in this sentence.\n"
    "3. The grammar in this sentence is incorrect.\n"
    "4. This sentence is poorly written.\n"
    "5. This sentence has a number of errors.\n"
)

FRENCH_OUTPUT = (
    "1. Je voudrais que tu viennes avec moi demain.\n"
    "2. J'aimerais que tu m'accompagnes demain.\n"
    "3. Pourrais-tu venir avec moi demain ?\n"
    "4. Je souhaite que tu sois avec moi demain.\n"
    "5. Est-ce que tu peux venir avec moi demain ?\n"
)


def chunks(text, size=8):
    """Split text into fixed-size chunks, simulating stream_generate output."""
    return [text[i:i + size] for i in range(0, len(text), size)]


class TestLanguageAndBatchParsePipeline:
    """detect_language + parse_suggestions working together."""

    def test_english_sentence_detected_and_parsed(self):
        lang = detect_language("This is a bad writed sentence.")
        suggestions = parse_suggestions(ENGLISH_OUTPUT)
        assert lang == "English"
        assert len(suggestions) == 5

    def test_french_accent_detected_and_parsed(self):
        lang = detect_language("J'ai été très fatigué aujourd'hui.")
        suggestions = parse_suggestions(FRENCH_OUTPUT)
        assert lang == "French"
        assert len(suggestions) == 5
        assert suggestions[0] == "Je voudrais que tu viennes avec moi demain."

    def test_french_function_words_detected_and_parsed(self):
        lang = detect_language("je ne sais pas quoi faire")
        suggestions = parse_suggestions(FRENCH_OUTPUT)
        assert lang == "French"
        assert len(suggestions) == 5

    def test_detected_language_appears_in_prompt(self):
        for sentence, expected_lang in [
            ("This needs fixing.", "English"),
            ("Ça doit être corrigé.", "French"),
        ]:
            lang = detect_language(sentence)
            assert lang == expected_lang
            prompt = f"Rewrite the following {lang} text"
            assert expected_lang in prompt

    def test_model_output_with_preamble_parses_correctly(self):
        output = "Here are 5 reformulations:\n" + ENGLISH_OUTPUT
        lang = detect_language("Fix this sentence.")
        suggestions = parse_suggestions(output)
        assert lang == "English"
        assert len(suggestions) == 5
        assert suggestions[0] == "This sentence contains grammatical errors."

    def test_partial_output_returns_only_available_suggestions(self):
        partial = (
            "1. First reformulation.\n"
            "2. Second reformulation.\n"
            "3. Third reformulation.\n"
        )
        lang = detect_language("Some text to fix here.")
        suggestions = parse_suggestions(partial)
        assert lang == "English"
        assert len(suggestions) == 3


class TestStreamParsePipeline:
    """stream_parse + detect_language: streaming path matches batch path."""

    def test_english_stream_matches_batch(self):
        assert list(stream_parse(chunks(ENGLISH_OUTPUT))) == parse_suggestions(ENGLISH_OUTPUT)

    def test_french_stream_matches_batch(self):
        assert list(stream_parse(chunks(FRENCH_OUTPUT))) == parse_suggestions(FRENCH_OUTPUT)

    def test_stream_with_single_character_chunks(self):
        result = list(stream_parse(chunks(ENGLISH_OUTPUT, size=1)))
        assert result == parse_suggestions(ENGLISH_OUTPUT)

    def test_stream_with_whole_lines_as_chunks(self):
        lines = ENGLISH_OUTPUT.splitlines(keepends=True)
        result = list(stream_parse(lines))
        assert len(result) == 5

    def test_stream_with_single_chunk(self):
        result = list(stream_parse([ENGLISH_OUTPUT]))
        assert result == parse_suggestions(ENGLISH_OUTPUT)

    def test_stream_partial_output(self):
        partial = (
            "1. First item.\n"
            "2. Second item.\n"
            "3. Third item.\n"
        )
        result = list(stream_parse(chunks(partial)))
        assert len(result) == 3
        assert result[0] == "First item."

    def test_stream_empty_input(self):
        assert list(stream_parse([])) == []

    def test_stream_no_numbered_items(self):
        assert list(stream_parse(["just some text without numbers"])) == []

    def test_stream_caps_at_five(self):
        long_output = "".join(f"{i}. Suggestion {i}.\n" for i in range(1, 9))
        result = list(stream_parse(chunks(long_output)))
        assert len(result) == 5

    def test_stream_french_chunked_preserves_accents(self):
        result = list(stream_parse(chunks(FRENCH_OUTPUT, size=4)))
        assert result[2] == "Pourrais-tu venir avec moi demain ?"
