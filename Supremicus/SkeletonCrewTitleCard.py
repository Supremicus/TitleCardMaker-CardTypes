from pathlib import Path
from collections import namedtuple
from random import choice as random_choice
from typing import Literal, Optional, TYPE_CHECKING

from pydantic import root_validator

from app.schemas.card_type import BaseCardTypeAllText

from modules.BaseCardType import (
    BaseCardType,
    ImageMagickCommands,
    Extra,
    CardDescription
)
from modules.Debug import log
from modules.EpisodeInfo2 import EpisodeInfo
from modules.RemoteFile import RemoteFile
from modules.Title import SplitCharacteristics

if TYPE_CHECKING:
    from app.models.preferences import Preferences
    from modules.Font import Font


BoxCoordinates = namedtuple('BoxCoordinates', ('x0', 'y0', 'x1', 'y1'))
VerticalPosition = Literal['top', 'center', 'bottom', 'random']


class SkeletonCrewTitleCard(BaseCardType):
    """
    CardType that produces title cards intended for the "Star Wars : 
    Skeleton Crew" series. Uses custom fonts to create the shows text
    and borders just like the shows logo and poster.
    """

    API_DETAILS = CardDescription(
        name='Skeleton Crew',
        identifier='Supremicus/SkeletonCrew',
        example='https://raw.githubusercontent.com/CollinHeist/TitleCardMaker-CardTypes/web-ui/Supremicus/SkeletonCrewTitleCard.preview.jpg',
        creators=[
            'Supremicus'
        ],
        source='remote',
        supports_custom_fonts=False,
        supports_custom_seasons=True,
        supported_extras=[
            Extra(
                name='Episode Text Color',
                identifier='episode_text_color',
                description='Color to use for the episode text',
                tooltip='Default is <c>transparent</c>.',
                default='transparent',
            ),
            Extra(
                name='Text Vertical Position',
                identifier='vertical_position',
                description='Position of all text',
                tooltip=(
                    'Either <v>top</v>, <v>center</v>, <v>bottom</v>, or '
                    '<v>random</v> to randomly select a position. '
                    'Default is <v>bottom</v>.'
                ),
                default='bottom',
            ),
        ],
        description=[
            'Title card intended for the "Star Wars : Skeleton Crew" television'
            'series with matching custom fonts to create the shows text and '
            'borders just like the shows logo. Customizable color and episode '
            'text color with the ability to change the vertical position.'
            
        ]
    )

    class CardModel(BaseCardTypeAllText):
        title_text: str
        season_text: str
        episode_text: str
        font_color: str
        font_size: float = 1.0
        font_vertical_shift: int = 0
        episode_text_color: str | None = None
        vertical_position: VerticalPosition = 'bottom'

        @root_validator(skip_on_failure=True)
        def validate_extras(cls, values: dict) -> dict:
            # Convert None colors to transparent for overlay image
            if values['episode_text_color'] is None:
                values['episode_text_color'] = 'transparent'

            return values

    """Characteristics for title splitting by this class"""
    TITLE_CHARACTERISTICS: SplitCharacteristics = {
        'max_line_width': 20,
        'max_line_count': 4,
        'style': 'top',
    }

    """How to name archive directories for this type of card"""
    ARCHIVE_NAME = 'SkeletonCrew'

    """Characteristics of title font"""
    TITLE_FONT = str(RemoteFile('Supremicus', 'ref/fonts/SkeletonCrew.otf'))
    TITLE_FONT_BOTTOM = RemoteFile('Supremicus', 'ref/fonts/SkeletonCrew-Offset.otf')
    TITLE_COLOR = '#FFFFFF'
    DEFAULT_FONT_CASE = 'title'

    """Characteristics of index text"""
    EPISODE_TEXT_FONT = RemoteFile('Supremicus', 'ref/fonts/SF-DistantGalaxy.ttf')
    EPISODE_TEXT_FORMAT = 'Episode {episode_number}'

    """Standard font replacements for the title font"""
    FONT_REPLACEMENTS = {
        '_': '', '~': '', '@': 'at', '*': '', '{': '(', '}': ')',
        '&': 'and',
    }

    """Whether this CardType uses season titles for archival purposes"""
    USES_SEASON_TITLE = True

    __slots__ = (
        'source_file',
        'output_file',
        'title_text',
        'season_text',
        'episode_text',
        'hide_season_text',
        'hide_episode_text',
        'font_color',
        'font_size',
        'font_vertical_shift',
        'episode_text_color',
        'vertical_position',
        '_title_coordinates',
        '_index_coordinates',
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
            font_size: float = 1.0,
            font_vertical_shift: int = 0,
            episode_text_color: str = None,
            vertical_position: VerticalPosition = 'bottom',
            blur: bool = False,
            grayscale: bool = False,
            preferences: Optional['Preferences'] = None,
            **unused,
        ) -> None:
        """Construct a new instance of this Card."""

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

        # Font customizations
        self.font_color = font_color
        self.font_size = font_size
        self.font_vertical_shift = font_vertical_shift

        # Optional extras
        self.episode_text_color = episode_text_color
        if vertical_position == 'random':
            vertical_position = random_choice(['bottom', 'center', 'top'])
        self.vertical_position = vertical_position

        # Put coordinates into memory
        self._title_coordinates = None
        self._index_coordinates = None


    def draw_border_command(self) -> ImageMagickCommands:
        """
        Draws the opposite corner radius border for the title text
        cutout the bottom border if theres a multiline title or close
        it if the title is single line

        Returns:
            List of ImageMagick commands necessary to draw the
            index box rectangle.
        """

        # No title, don't make border
        if not self.title_text:
            return []

        x0, y0, x1, y1 = self.get_title_coordinates()

        # Pull in bottom title text to measure bottom border coditional
        title_main_text, title_bottom_text = self.process_title_text(self.title_text)

        # Get width of title main text
        main_text_width = [
            f'-font "{self.TITLE_FONT}"',
            f'-pointsize {200 * self.font_size}',
            f'-annotate +0+0 "{title_main_text}"',
        ]
        main_text_width, _ = self.image_magick.get_text_dimensions(main_text_width)

        # Get width of title bottom text
        bottom_text_width_command = [
            f'-font "{self.TITLE_FONT}"',
            f'-pointsize {200 * self.font_size}',
            f'-annotate +0+0 "{title_bottom_text}"',
        ]
        bottom_text_width, _ = self.image_magick.get_text_dimensions(bottom_text_width_command)

        # Calculate x_start and x_end for both main and bottom text
        main_x_start, main_x_end = (self.WIDTH - main_text_width) / 2, (self.WIDTH + main_text_width) / 2
        bottom_x_start, bottom_x_end = (self.WIDTH - bottom_text_width) / 2, (self.WIDTH + bottom_text_width) / 2

        # Compare and adjust only if bottom text is wider than main text and pad x0 and x1
        # This is incase of long title names which the show seems to have
        scaled_offset = 72 * self.font_size
        if bottom_x_start < main_x_start or bottom_x_end > main_x_end:
                x0 -= sum([scaled_offset, max(0, x0 - bottom_x_start)])
                x1 += sum([scaled_offset, max(0, bottom_x_end - x1)])

        # Additional offsets necessary for equal padding
        bottom_x_start -= 36
        bottom_x_end += 36

        # Adjust the lines slightly depending on what character the
        # bottom title text starts or ends with to style with the
        # character and not width bounds (20px from line to character)

        # Dictionary for uppercase characters with their adjustments
        # Negative numbers represent -=, positive numbers represent +=
        upper_chars = {
            'A': 40, 'C': 12, 'E': 12, 'G': 12, 'J': 40, 'M': 24, 'O': 10,
            'Q': 10, 'V': 10, 'W': 5, 'X': 10, 'Y': 10, 'Z': 9, '2': 12,
            '4': 32, '6': 34, '0': 10
        }

        # Dictionary for lowercase characters with their adjustments
        lower_chars = {
            'a': -32, 'b': -2, 'd': -10, 'g': -10, 'k': -18, 'l': -36, 
            'm': -22, 'o': -12, 'p': -4, 'q': -12, 'r': -16, 's': -6,
            'v': -6, 'w': -6, 'y': -12, '2': -4, '3': -6, '5': -8,
            '6': -23, '8': -6, '9': -8, '0': -14
        }

        # Scale the character adjustments based on font size override
        scaled_upper_chars = {c: int(i * self.font_size) for c, i in upper_chars.items()}
        scaled_lower_chars = {c: int(i * self.font_size) for c, i in lower_chars.items()}

        # Check the first character
        if title_bottom_text:
            char = title_bottom_text[0]
            if char in scaled_upper_chars:
                bottom_x_start += scaled_upper_chars[char]

        # Check the last character
        if title_bottom_text:
            char = title_bottom_text[-1]
            if char in scaled_lower_chars:
                bottom_x_end += scaled_lower_chars[char]

        return [
            f'-fill transparent',
            f'-stroke "{self.font_color}"', 
            f'-strokewidth 16',
            # Whitespace at end to keep as single draw command
            f'-draw "arc {x0+10},{y0+130} {x0+130},{y0+10} 180,270 ',
            f'line {x0+65},{y0+10} {x1-30},{y0+10} ',
            f'arc {x1-60},{y0+10} {x1},{y0+60} 270,360 ',
            f'line {x1},{y0+30} {x1},{y1-65} ',
            f'arc {x1},{y1-130} {x1-130},{y1-10} 0,90 ',
            # Open bottom border
        ] + ([
            f'line {x0+30},{y1-10} {bottom_x_start},{y1-10} ', #left x0
            f'arc {bottom_x_start+10},{y1-10} {bottom_x_start-10},{y1+6} 270,360 ',
            f'line {x1-65},{y1-10} {bottom_x_end},{y1-10} ', #right x1
            f'arc {bottom_x_end+10},{y1-10} {bottom_x_end-10},{y1-26} 90,180 ',
        ] if title_bottom_text else [
            # Close off bottom border if no title bottom text
            f'line {x1-65},{y1-10} {x0+30},{y1-10} ',
        ]) + [
            f'arc {x0+60},{y1-10} {x0+10},{y1-60} 90,180 ',
            f'line {x0+10},{y1-30} {x0+10},{y0+65}"',
            f'-stroke none',
        ]


    def draw_index_box_command(self) -> ImageMagickCommands:
        """
        Draws the opposite corner radius box for the index text

        Returns:
            List of ImageMagick commands necessary to draw the
            index box rectangle.
        """

        # All text hidden, don't make the box
        if self.hide_season_text and self.hide_episode_text:
            return []

        x0, y0, x1, y1 = self.get_index_coordinates()

        return [
            f'-fill "{self.font_color}"',
            f'-draw "path \'M {x0+20},{y0} A 20,20 0 0,0 {x0},{y0+20} \
            L {x0+20},{y0} L {x1-10},{y0} \
            A 10,10 0 0,1 {x1},{y0+10} \
            L {x1},{y0+10} L {x1},{y1-20} \
            A 20,20 0 0,1 {x1-20},{y1} \
            L {x1-20},{y1} L {x0+10},{y1} \
            A 10,10 0 0,1 {x0},{y1-10} \
            L {x0},{y1-10} L {x0},{y0+20} Z\'"'
        ]


    def process_title_text(self, title_text):
        """
        Process title text to split the last line off so
        we can change it's font in the title text command.

        Returns:
            title_text_main: all but last line of title text combined
            title_text_bottom: last line of title text
        """
        # Check for line breaks, return as is if single line
        if '\n' not in title_text:
            return title_text, None

        lines = title_text.split('\n')
        title_text_bottom = lines[-1]
        title_text_main = '\n'.join(lines[:-1])
        
        return title_text_main, title_text_bottom


    def get_title_coordinates(self) -> BoxCoordinates:
        """
        Get the coordinates of the bounding box around the title.

        Returns:
            BoxCoordinates of the bounding box.
        """

        if self._title_coordinates is None:
            # Get dimensions of title text
            width, height = self.image_magick.get_text_dimensions(
                self.title_text_commands,
                line_count=len(self.title_text.splitlines()),
            )

            # Get start coordinates of the bounding box
            x_start, x_end = (self.WIDTH - width) / 2, (self.WIDTH + width) / 2

            # Adjust y start position based on gravity and add vertical shift
            # And adjust offset for single line titles to match 2 line titles
            if self.vertical_position == 'top':
                y_offset = 157
                y_offset += self.font_vertical_shift
                y_start = y_offset
            elif self.vertical_position == 'center':
                y_offset = 30
                y_offset += self.font_vertical_shift
                y_start = (self.HEIGHT - height) / 2 + y_offset
            else:
                y_offset = 217 if '\n' not in self.title_text else 60
                y_offset += self.font_vertical_shift
                y_start = self.HEIGHT - height - y_offset

            y_end = y_start + height

            # Additional offsets necessary for equal padding
            x_start -= 56
            x_end += 44
            y_start -= 40
            y_end += 16
            # Adjust for font size changes over multi-line
            if len(self.title_text.splitlines()) >= 2:
                # Font size * user input font size * 65%
                y_end -= (200 * self.font_size) * 0.65
            else:
                y_end += 20

            self._title_coordinates = BoxCoordinates(x_start, y_start, x_end, y_end)

        return self._title_coordinates


    def get_index_coordinates(self) -> BoxCoordinates:
        """
        Get the coordinates of the bounding box around the index text.

        Returns:
            BoxCoordinates of the bounding box.
        """

        if self._index_coordinates is None:
            # Ensure title coordinates are calculated without causing
            # recursion as a precaution
            if self._title_coordinates is None:
                self._title_coordinates = self.get_title_coordinates()

            # Get dimensions of index text
            width, height = self.image_magick.get_text_dimensions(
                self.index_text_commands()
            )

            # Calculate y offset based on title's coordinates
            title_coordinates = self._title_coordinates
            y_offset = (self.HEIGHT - title_coordinates.y0) - 35

            # Get start coordinates of the bounding box
            x_start, x_end = (self.WIDTH - width) / 2, (self.WIDTH + width) / 2
            y_start, y_end = self.HEIGHT - y_offset - 50, self.HEIGHT - y_offset

            # Additional offsets for equal padding
            x_start -= 24
            x_end += 22

            self._index_coordinates = BoxCoordinates(x_start, y_start, x_end, y_end)

        return self._index_coordinates


    @property
    def title_text_commands(self) -> ImageMagickCommands:
        """Subcommands required to add the title text."""

        # If no title text, return empty commands
        if not self.title_text:
            return []

        # Split up text so we can change font of bottom text
        title_main_text, title_bottom_text = self.process_title_text(self.title_text)

        # Font size
        font_size = 200 * self.font_size

        # Determine gravity prefix based on vertical position
        # And adjust offset for single line titles to match 2 line titles
        if self.vertical_position == 'top':
            gravity_prefix = 'north'
            y_offset = 157
        elif self.vertical_position == 'center':
            gravity_prefix = 'center'
            y_offset = 30
        else:  # Assuming 'bottom' or any other value defaults to 'south'
            gravity_prefix = 'south'
            y_offset = 217 if '\n' not in self.title_text else 60

        # Text offsets
        y = y_offset + self.font_vertical_shift

        return [
            # Add title text
            f'-font "{self.TITLE_FONT}"',
            f'-gravity {gravity_prefix}',
            f'-pointsize {font_size}',
            f'-background transparent',
            f'-fill "{self.font_color}"',
            fr'\(',
            f'-font "{self.TITLE_FONT}"',
            f'label:"{title_main_text}"',
        ] + ([
            # Conditionally add bottom title text if it exists
            f'-font "{self.TITLE_FONT_BOTTOM}"',
            f'label:"{title_bottom_text}"',
            f'-append',
        ] if title_bottom_text else []) + [
            fr'\)',
            f'-geometry +0{y:+}',
            f'-composite',
        ]


    def index_text_commands(self) -> ImageMagickCommands:
        """Subcommand for adding the index text to the image."""

        # All text hidden, return empty commands
        if self.hide_season_text and self.hide_episode_text:
            return []

        # Set index text based on which text is hidden/not
        if self.hide_season_text:
            index_text = self.episode_text
        elif self.hide_episode_text:
            index_text = self.season_text
        else:
            index_text = f'{self.season_text} • {self.episode_text}'

        # Grab title coordinates for offset
        title_coordinates = self.get_title_coordinates()

        # Text offsets
        y = (self.HEIGHT - title_coordinates.y0) - 35

        return [
            f'-kerning 0',
            f'-pointsize 50',
            f'-gravity south',
            f'-font "{self.EPISODE_TEXT_FONT}"',
            f'-fill {self.episode_text_color}',
            f'-stroke none',
            f'-antialias',
            f'-annotate +0{y:+} "{index_text}"',
        ]


    def create_overlay_image(self) -> Path:
        """
        Create the overlay image combining the title border,
        index box and index text

        Returns:
            Path to the created image. This is a temporary image which
            must be deleted afterwards.
        """

        # Get random filename for intermediate image
        # PNG for transparency and quality
        image = self.image_magick.get_random_filename(
            self.source_file, extension='png'
        )

        self.image_magick.run([
            f'convert',
            f'-size "{self.TITLE_CARD_SIZE}"',
            f'xc:transparent',
            # Combine title border and index box
            *self.draw_border_command(),
            *self.draw_index_box_command(),
            # Add index text
            *self.index_text_commands(),
            f'"{image.resolve()}"',
        ])

        return image


    @staticmethod
    def is_custom_font(font: 'Font') -> Literal[False]:
        """
        Determines whether the given font characteristics constitute a
        default or custom font.
        
        Args:
            font: The Font being evaluated.
        
        Returns:
            False, as custom fonts are not used.
        """

        return False


    @staticmethod
    def is_custom_season_titles(
            custom_episode_map: bool,
            episode_text_format: str,
        ) -> bool:
        """
        Determine whether the given attributes constitute custom or
        generic season titles.

        Args:
            custom_episode_map: Whether the EpisodeMap was customized.
            episode_text_format: The episode text format in use.

        Returns:
            True if custom season titles are indicated, False otherwise.
        """

        return (
            custom_episode_map
            or episode_text_format != SkeletonCrewTitleCard.EPISODE_TEXT_FORMAT
        )


    @staticmethod
    def SEASON_TEXT_FORMATTER(episode_info: EpisodeInfo) -> str:
        """
        Fallback season title formatter.

        Args:
            episode_info: Info of the Episode whose season text is being
                determined.

        Returns:
            'Specials' if the season number is 0; otherwise just
            'Season {x}'.
        """

        if episode_info.season_number == 0:
            return 'Specials'

        return 'Season {season_number}'


    def create(self) -> None:
        """
        Make the necessary ImageMagick and system calls to create this
        object's defined title card.
        """

        # Layers are ordered as:
        # [Source Image] | [Overlay image]

        # TemporaryPath object which will be deleted
        overlay_image = self.create_overlay_image()

        self.image_magick.run([
            f'convert',
            # Layer 0 is the source image which will be the background
            fr'\(',
            f'"{self.source_file.resolve()}"',
            # Resize and apply styles to source image
            *self.resize_and_style,
            fr'\)',
            # Layer 1 is the overlay image
            f'"{overlay_image.resolve()}"',
            # Use compose over to combine
            f'-compose over',
            f'-composite',
            # Add title text here over overlay layer because of transparentcy
            *self.title_text_commands,
            # Attempt to overlay mask
            *self.add_overlay_mask(self.source_file),
            # Create card
            *self.resize_output,
            f'"{self.output_file.resolve()}"',
        ])

        self.image_magick.delete_intermediate_images(
            overlay_image
        )
