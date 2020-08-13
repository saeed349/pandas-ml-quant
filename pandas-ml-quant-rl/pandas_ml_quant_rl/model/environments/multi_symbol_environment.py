import math
import re
from typing import Union, List, Callable, Tuple, Any
import gym
from pandas_ml_common import pd, np
from pandas_ml_quant_rl.cache.abstract_cache import Cache
from pandas_ml_quant_rl.cache import NoCache
from pandas_ml_quant_rl.renderer.abstract_renderer import Renderer
from pandas_ml_utils import FeaturesAndLabels
from pandas_ml_utils.ml.data.extraction import extract_features


class RandomAssetEnv(gym.Env):

    def __init__(self,
                 features_and_labels: FeaturesAndLabels,
                 symbols: Union[str, List[str]],
                 action_space: gym.Space,
                 reward_provider: Callable[[Any, np.ndarray, np.ndarray, np.ndarray], Tuple[float, bool]] = None,
                 pct_train_data: float = 0.8,
                 max_steps: int = None,
                 use_cache: Cache = NoCache(),
                 renderer: Renderer = Renderer()
                 ):
        super().__init__()
        self.max_steps = math.inf if max_steps is None else max_steps
        self.features_and_labels = features_and_labels
        self.reward_provider = reward_provider
        self.pct_train_data = pct_train_data
        self.renderer = renderer

        # define spaces
        self.action_space = action_space
        self.observation_space = None

        # define execution mode
        self.cache = use_cache
        self.mode = 'train'
        self.done = True

        # load symbols available to randomly draw from
        if isinstance(symbols, str):
            with open(symbols) as f:
                self.symbols = np.array(re.split("[\r\n]|[\n]|[\r]", f.read()))
        else:
            self.symbols = symbols

        # finally make a dummy initialisation
        self._init()

    def as_train(self) -> Tuple['RandomAssetEnv', pd.Series] :
        # note that shallow copy is shuffling due to the _init call
        copy = self._shallow_copy()
        copy.mode = 'train'
        return copy, self._current_state()

    def as_test(self) -> Tuple['RandomAssetEnv', pd.Series] :
        # note that shallow copy is shuffling due to the _init call
        copy = self._shallow_copy()
        copy.mode = 'test'
        return copy, self._current_state()

    def as_predict(self) -> Tuple['RandomAssetEnv', pd.Series] :
        # note that shallow copy is shuffling due to the _init call
        copy = self._shallow_copy()
        copy.mode = 'predict'
        return copy, self._current_state()

    def _shallow_copy(self):
        # note that shallow copy is shuffling due to the _init call
        return RandomAssetEnv(
            self.features_and_labels,
            self.symbols,
            self.action_space,
            self.reward_provider,
            self.pct_train_data,
            self.max_steps,
            self.cache,
            self.renderer
        )

    def step(self, action):
        reward, game_over = self.reward_provider(
            action,
            self._labels.iloc[[self._state_idx]]._.values,
            self._sample_weights.iloc[[self._state_idx]]._.values if self._sample_weights is not None else None,
            self._gross_loss.iloc[[self._state_idx]]._.values if self._gross_loss is not None else None
        )

        old_state = self._current_state()
        self._state_idx += 1
        self.done = game_over \
                    or self._state_idx >= self._last_index \
                    or self._state_idx > (self._start_idx + self.max_steps)

        new_state = self._current_state()
        self.renderer.put_action(old_state, action, new_state, reward, self.done)
        return new_state, reward, self.done, {}

    def render(self, mode='human'):
        self.renderer.render(mode)

    def reset(self):
        return self._init()

    def _init(self):
        self._symbol = np.random.choice(self.symbols, 1).item()
        self._df = self.cache.get_data_or_fetch(self._symbol)

        if self.mode in ['train', 'test']:
            self._features, self._labels, self._targets, self._sample_weights, self._gross_loss = \
                self.cache.get_feature_frames_or_fetch(self._df, self._symbol, self.features_and_labels)

            if self.mode == 'train':
                self._last_index = int(len(self._features) * 0.8)
                # allow at least one step
                self._state_idx = np.random.randint(1, self._last_index - 1, 1).item()
            if self.mode == 'test':
                self._last_index = len(self._features)
                # allow at least one step
                self._state_idx = np.random.randint(int(len(self._features) * 0.8), len(self._features) - 1, 1).item()

        else:
            # only extract features!
            _, self._features, self._targets = extract_features(self._df, self.features_and_labels)
            self._last_index = len(self._features)
            self._labels = pd.DataFrame({})
            self._sample_weights = pd.DataFrame({})
            self._gross_loss = pd.DataFrame({})
            self._state_idx = 0

        if self.observation_space is None:
            self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=self._features.iloc[[-1]]._.values.shape[1:])

        self._start_idx = self._state_idx
        self.done = self._state_idx >= self._last_index
        return self._current_state()

    def _current_state(self):
        # make sure to return it as a batch of size one therefore use list of state_idx
        return self._features.iloc[[self._state_idx]]

# ...
# TODO later allow features to be a list of feature sets echa witha possible different shape
