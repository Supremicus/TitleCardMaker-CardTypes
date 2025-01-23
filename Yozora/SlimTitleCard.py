from pathlib import Path
from typing import Optional, TYPE_CHECKING

from app.schemas.card_type import BaseCardTypeCustomFontAllText

from modules.BaseCardType import (
    BaseCardType,
    CardDescription,
    Extra,
    ImageMagickCommands,
)
from modules.Debug import log
from modules.RemoteFile import RemoteFile
from modules.Title import SplitCharacteristics

if TYPE_CHECKING:
    from app.models.preferences import Preferences
    from modules.Font import Font


class SlimTitleCard(BaseCardType):
    """
    Card type closely following the Standard Title Card but with slimmed
    down margins to save space.
    """

    API_DETAILS = CardDescription(
        name='Slim',
        identifier='Yozora/SlimTitleCard',
        example=(
            'https://camo.githubusercontent.com/8eb09f530888a23bc9279f26fff0d'
            '6ee0ea82f998137560f24f042bb9a0e4639/68747470733a2f2f63646e2e6469'
            '73636f72646170702e636f6d2f6174746163686d656e74732f39373531303830'
            '33333533313231393937392f3937373631343933373435373330333630322f53'
            '30314530342e6a7067'
        ),
        creators=['Yozora', 'CollinHeist'],
        source='remote',
        supports_custom_fonts=True,
        supports_custom_seasons=True,
        supported_extras=[],
        description=[
            'Card type closely following the Standard Title Card but with '
            'slimmed down margins to save space.',
        ]
    )

    class CardModel(BaseCardTypeCustomFontAllText):
        omit_gradient: bool = False

    """Directory where all reference files used by this card are stored"""
    REF_DIRECTORY = Path(__file__).parent.parent / 'ref'

    """Characteristics for title splitting by this class"""
    TITLE_CHARACTERISTICS: SplitCharacteristics = {
        'max_line_width': 45,
        'max_line_count': 3,
        'style': 'bottom',
    }

    """Default font and text color for episode title text"""
    TITLE_FONT = str(RemoteFile('Yozora', 'ref/slim/Comfortaa-Regular.ttf'))
    TITLE_COLOR = '#FFFFFF'

    """Default characters to replace in the generic font"""
    FONT_REPLACEMENTS = {
        '…': '...', '[': '(', ']': ')', '(': '[', ')': ']', '―': '-'
    }

    """Whether this CardType uses season titles for archival purposes"""
    USES_SEASON_TITLE = True

    """Slim class has specialized archive name"""
    ARCHIVE_NAME = 'Slim Style'

    """Source path for the gradient image overlayed over all title cards"""
    __GRADIENT_IMAGE = RemoteFile('Yozora', 'ref/slim/GRADIENT.png')

    """Default fonts and color for series count text"""
    SEASON_COUNT_FONT = RemoteFile('Yozora', 'ref/slim/Comfortaa-SemiBold.ttf')
    EPISODE_COUNT_FONT = RemoteFile('Yozora', 'ref/slim/Comfortaa-Regular.ttf')
    SERIES_COUNT_TEXT_COLOR = '#a5a5a5'

    __slots__ = (
        'source_file', 'output_file', 'title_text', 'season_text',
        'episode_text', 'hide_season_text', 'hide_episode_text', 'font_color',
        'font_file', 'font_interline_spacing', 'font_kerning', 'font_size',
        'font_stroke_width', 'font_vertical_shift', 'omit_gradient',
    )


    def __init__(self, *,
            source_file: Path,
            card_file: Path,
            title_text: str,
            season_text: str,
            episode_text: str,
            hide_season_text: bool = False,
            hide_episode_text: bool = False,
            font_color: str = TITLE_COLOR,
            font_file: str = TITLE_FONT,
            font_interline_spacing: int = 0,
            font_kerning: float = 1.0,
            font_size: float = 1.0,
            font_stroke_width: float = 1.0,
            font_vertical_shift: int = 0,
            blur: bool = False,
            grayscale: bool = False,
            omit_gradient: bool = False,
            preferences: Optional['Preferences'] = None,
            **unused,
        ) -> None:
        
        # Initialize the parent class - this sets up an ImageMagickInterface
        super().__init__(blur, grayscale, preferences=preferences)

        self.source_file = source_file
        self.output_file = card_file

        # Ensure characters that need to be escaped are
        self.title_text = self.image_magick.escape_chars(title_text)
        self.season_text = self.image_magick.escape_chars(season_text)
        self.episode_text = self.image_magick.escape_chars(episode_text)
        self.hide_season_text = hide_season_text
        self.hide_episode_text = hide_episode_text

        # Font characteristics
        self.font_color = font_color
        self.font_file = font_file
        self.font_interline_spacing = font_interline_spacing
        self.font_kerning = font_kerning
        self.font_size = font_size
        self.font_stroke_width = font_stroke_width
        self.font_vertical_shift = font_vertical_shift

        # Extras
        self.omit_gradient = omit_gradient


    @property
    def __title_text_global_effects(self) -> ImageMagickCommands:
        """
        ImageMagick commands to implement the title text's global
        effects. Specifically the the font, kerning, fontsize, and
        center gravity.
        """

        font_size = 157.41 * self.font_size
        interline_spacing = -22 + self.font_interline_spacing
        kerning = -1.25 * self.font_kerning

        return [
            f'-font "{self.font_file}"',
            f'-kerning {kerning}',
            f'-interword-spacing 50',
            f'-interline-spacing {interline_spacing}',
            f'-pointsize {font_size}',
            f'-gravity south',
        ]   


    @property
    def __title_text_black_stroke(self) -> ImageMagickCommands:
        """
        ImageMagick commands to implement the title text's black stroke.
        """

        stroke_width = 1.0 * self.font_stroke_width

        return [
            f'-fill black',
            f'-stroke black',
            f'-strokewidth {stroke_width}',
        ]


    @property
    def __series_count_text_global_effects(self) -> ImageMagickCommands:
        """
        ImageMagick commands for global text effects applied to all series count
        text (season/episode count and dot).
        """

        return [
            f'-kerning 5.42',
            f'-pointsize 67.75',
        ]


    @property
    def __series_count_text_black_stroke(self) -> ImageMagickCommands:
        """
        ImageMagick commands for adding the necessary black stroke effects to
        series count text.
        """

        return [
            f'-fill black',
            f'-stroke black',
            f'-strokewidth 6',
        ]


    @property
    def __series_count_text_effects(self) -> ImageMagickCommands:
        """Necessary text effects to the series count text."""

        return [
            f'-fill "{self.SERIES_COUNT_TEXT_COLOR}"',
            f'-stroke "{self.SERIES_COUNT_TEXT_COLOR}"',
            f'-strokewidth 0.75',
        ]


    @property
    def title_text_command(self) -> ImageMagickCommands:
        """Add title text to the source image."""

        vertical_shift = 100 + self.font_vertical_shift

        return [
            *self.__title_text_global_effects,
            *self.__title_text_black_stroke,
            f'-annotate +0+{vertical_shift} "{self.title_text}"',
            f'-fill "{self.font_color}"',
            f'-annotate +0+{vertical_shift} "{self.title_text}"',
        ]


    @property
    def index_text_command(self) -> ImageMagickCommands:
        """Subcommand for adding the index text to the source image."""

        if self.hide_season_text and self.hide_episode_text:
            return []

        if self.hide_season_text:
            return [
                *self.__series_count_text_global_effects,
                f'-font "{self.EPISODE_COUNT_FONT}"',
                f'-gravity center',
                *self.__series_count_text_black_stroke,
                f'-annotate +0+697.2 "{self.episode_text}"',
                *self.__series_count_text_effects,
                f'-annotate +0+697.2 "{self.episode_text}"',
            ]
        
        if self.hide_episode_text:
            return [
                *self.__series_count_text_global_effects,
                f'-font "{self.SEASON_COUNT_FONT}"',
                f'-gravity center',
                *self.__series_count_text_black_stroke,
                f'-annotate +0+697.2 "{self.season_text}"',
                *self.__series_count_text_effects,
                f'-annotate +0+697.2 "{self.season_text}"',
            ]

        return [
            f'-background transparent',
            f'+interword-spacing',
            f'-gravity south',
            fr'\(',
            *self.__series_count_text_global_effects,
            *self.__series_count_text_black_stroke,
            f'-font "{self.SEASON_COUNT_FONT}"',
            f'label:"{self.season_text}"',
            f'label:"• "',
            f'-font "{self.EPISODE_COUNT_FONT}"',
            f'label:"{self.episode_text}"',
            f'+smush 15',
            fr'\)',
            f'-geometry +0+35',
            f'-composite',

            fr'\(',
            *self.__series_count_text_global_effects,
            *self.__series_count_text_effects,
            f'-font "{self.SEASON_COUNT_FONT}"',
            f'label:"{self.season_text}"',
            f'label:"• "',
            f'-font "{self.EPISODE_COUNT_FONT}"',
            f'label:"{self.episode_text}"',
            f'+smush 18',
            fr'\)',
            f'-geometry +0+35',
            f'-composite',
        ]


    @staticmethod
    def is_custom_font(font: 'Font') -> bool:
        """
        Determines whether the given font characteristics constitute a
        default or custom font.
        
        Args:
            font: The Font being evaluated.
        
        Returns:
            True if a custom font is indicated, False otherwise.
        """

        return (
            font.color != SlimTitleCard.TITLE_COLOR
            or font.file != SlimTitleCard.TITLE_FONT
            or font.interline_spacing != 0
            or font.kerning != 1.0
            or font.size != 1.0
            or font.stroke_width != 1.0
            or font.vertical_shift != 0
        )


    @staticmethod
    def is_custom_season_titles(
            custom_episode_map: bool,
            episode_text_format: str,
        ) -> bool:
        """
        Determines whether the given attributes constitute custom or
        generic season titles.
        
        Args:
            custom_episode_map: Whether the EpisodeMap was customized.
            episode_text_format: The episode text format in use.
        
        Returns:
            True if custom season titles are indicated, False otherwise.
        """

        # Nonstandard episode text format
        if episode_text_format != 'EPISODE {episode_number}':
            return True

        return custom_episode_map


    def create(self) -> None:
        """Create this object's defined title card."""

        if self.omit_gradient:
            gradient_command = []
        else:
            gradient_command = [
                f'"{self.__GRADIENT_IMAGE.resolve()}"',
                f'-composite',
            ]

        self.image_magick.run([
            f'convert "{self.source_file.resolve()}"',
            *self.resize_and_style,
            # Add gradient
            *gradient_command,
            # Add title and index text
            *self.title_text_command,
            *self.index_text_command,
            # Attempt to overlay mask
            *self.add_overlay_mask(self.source_file),
            # Create card
            *self.resize_output,
            f'"{self.output_file.resolve()}"',
        ])
