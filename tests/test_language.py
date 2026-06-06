from tinyblabla.language import detect_language


class TestDetectLanguageFrench:
    def test_accent_char_e_acute(self):
        assert detect_language("J'ai été très fatigué") == "French"

    def test_accent_char_cedilla(self):
        assert detect_language("Ça va bien") == "French"

    def test_accent_char_e_grave(self):
        assert detect_language("Il est très sympa") == "French"

    def test_accent_char_a_grave(self):
        assert detect_language("Il va là-bas") == "French"

    def test_accent_char_oe_ligature(self):
        assert detect_language("Le cœur bat vite") == "French"

    def test_french_function_words(self):
        # No accents, but ≥2 French function words
        assert detect_language("le chat est sur le tapis") == "French"

    def test_french_function_words_threshold(self):
        # "je" + "ne" + "pas" = 3 matches → French
        assert detect_language("je ne sais pas") == "French"

    def test_typical_french_sentence(self):
        assert detect_language("Je veux que tu viennes avec moi demain") == "French"


class TestDetectLanguageEnglish:
    def test_plain_english(self):
        assert detect_language("The cat is sitting on the mat") == "English"

    def test_english_with_no_french_words(self):
        assert detect_language("Hello world this is a test") == "English"

    def test_single_french_word_not_enough(self):
        # Only 1 French function word — below threshold
        assert detect_language("the le table") == "English"

    def test_empty_string(self):
        assert detect_language("") == "English"

    def test_numbers_only(self):
        assert detect_language("12345") == "English"

    def test_typical_english_sentence(self):
        assert detect_language("This sentence needs better grammar and style") == "English"
