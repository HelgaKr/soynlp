from soynlp.noun import LRNounExtractor_v2
from soynlp.predicator import PredicatorExtractor
from soynlp.utils import LRGraph


class POSExtractor:

    def __init__(self, verbose=True, extract_noun_pos_feature=True,
        extract_determiner=True, ensure_normalized=True, extract_eomi=True,
        extract_stem=True):

        self._verbose = verbose
        # noun extraction
        self._extract_noun_pos_feature = extract_noun_pos_feature
        self._extract_determiner = extract_determiner
        self._ensure_normalized = ensure_normalized
        # predicator extraction
        self._extract_eomi = extract_eomi
        self._extract_stem = extract_stem

    def extract(self, sents,
        # noun init
        min_num_of_noun_features=1, max_frequency_when_noun_is_eojeol=30,
        # noun extraction
        min_noun_score=0.3, min_noun_frequency=1, min_eojeol_frequency=1,
        # noun domain pos features
        ignore_features=None, min_noun_frequency_in_pos_extraction=100,
        min_pos_score=0.3, min_pos_feature_frequency=1000,
        min_num_of_unique_lastchar=4, min_entropy_of_lastchar=0.5,
        min_noun_entropy=1.5,
        # predicator train
        min_predicator_frequency=10,
        # Eomi extractor
        min_num_of_eomi_features=5, min_eomi_score=0.3, min_eomi_frequency=1,
        # Stem extractor
        min_num_of_unique_R_char=10, min_entropy_of_R_char=0.5,
        min_entropy_of_R=1.5, min_stem_score=0.7, min_stem_frequency=100):

        nouns = self._extract_nouns(sents, min_num_of_noun_features,
            max_frequency_when_noun_is_eojeol, min_noun_score,
            min_noun_frequency, min_eojeol_frequency,
            # noun domain pos features
            ignore_features, min_noun_frequency_in_pos_extraction,
            min_pos_score, min_pos_feature_frequency,
            min_num_of_unique_lastchar, min_entropy_of_lastchar,
            min_noun_entropy)

        predicators = self._extract_predicators(nouns, sents)

        nouns_, removals, predicators = self._remove_confused_nouns(
            nouns, predicators)

        wordtags = {
            'Noun': nouns_,
            'Eomi': self.predicator_extractor._eomis,
            'Adjective': {},
            'AdjectiveStem': {},
            'Verb': {},
            'VerbStem': {},
        }

        return wordtags

    def _extract_nouns(self, sents,
        # noun init
        min_num_of_features=1, max_frequency_when_noun_is_eojeol=30,
        # noun extraction
        min_noun_score=0.3, min_noun_frequency=1, min_eojeol_frequency=1,
        # noun domain pos features
        ignore_features=None, min_noun_frequency_in_pos_extraction=100,
        min_pos_score=0.3, min_pos_feature_frequency=1000,
        min_num_of_unique_lastchar=4, min_entropy_of_lastchar=0.5,
        min_noun_entropy=1.5):

        self.noun_extractor = LRNounExtractor_v2(
            extract_pos_feature = False,
            extract_determiner = self._extract_determiner,
            ensure_normalized = self._ensure_normalized,
            verbose = self._verbose,
            min_num_of_features = min_num_of_features,
            max_frequency_when_noun_is_eojeol = max_frequency_when_noun_is_eojeol
        )

        self.noun_extractor.train(sents, min_eojeol_frequency)

        if self._extract_noun_pos_feature:
            self.noun_extractor.extract_domain_pos_features(None, # noun candidates
                ignore_features, True, # append_extracted_features
                min_noun_score, min_noun_frequency_in_pos_extraction, min_pos_score,
                min_pos_feature_frequency, min_num_of_unique_lastchar,
                min_entropy_of_lastchar, min_noun_entropy)

        nouns = self.noun_extractor.extract(min_noun_score,
            min_noun_frequency, reset_lrgraph=False)

        return nouns

    def _extract_predicators(self, nouns, sents):

        # prepare predicator_lrgraph
        predicator_lrgraph = LRGraph(self.noun_extractor.lrgraph._lr)
        noun_pos_features = {r for r in self.noun_extractor._pos_features}
        noun_pos_features.update({r for r in self.noun_extractor._common_features})

        # predicator extraction
        self.predicator_extractor = PredicatorExtractor(
            nouns,
            noun_pos_features,
            extract_eomi = self._extract_eomi,
            extract_stem = self._extract_stem,
            verbose = self._verbose
        )

        self.predicator_extractor.train(sents)
        predicators = self.predicator_extractor.extract()

        return predicators

    def _remove_confused_nouns(self, nouns, predicators):
        nouns_ = {}
        removals = {}

        for noun, score in nouns.items():
            if self._is_noun_predicator_compound(noun, nouns, predicators):
                removals[noun] = score
            else:
                nouns_[noun] = score
        return nouns_, removals, predicators

    def _is_noun_predicator_compound(self, noun, nouns, predicators):
        def is_noun_josa(prefix):
            if prefix in nouns:
                return True
            for i in range(2, len(prefix)):
                l, r = prefix[:i], prefix[i:]
                if (l in nouns) and is_pos_feature(r):
                    return True
            return False

        def is_pos_feature(r):
            return ((r in predicators) or
                    (r in self.noun_extractor._pos_features) or
                    (r in self.noun_extractor._common_features))

        if noun in predicators:
            return True

        n = len(noun)
        for i in range(-1, -n + 1, -1):
            prefix, suffix = noun[:i], noun[i:]
            if (prefix in predicators) and (suffix in predicators):
                return True
            if is_noun_josa(prefix) and (suffix in predicators):
                return True
        return False

    def _separate_verb_adjective(self, predicators):
        raise NotImplemented