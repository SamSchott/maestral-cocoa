# -*- coding: utf-8 -*-

# external imports
import toga
from toga.style import Pack
from toga.constants import COLUMN, ROW, BOLD, CENTER
import markdown2

# local imports
from . import __url__
from .private.widgets import (
    Window, DialogButtons, VibrantBox,
    Label, RichMultilineTextInput, FollowLinkButton
)
from .private.constants import VisualEffectMaterial, WORD_WRAP
from .utils import clear_background, async_call, run_maestral_async, alert_sheet


# NSAlert's are the preferred way of alerting the user. However, we use our own dialogs
# in the following cases:
#
#  - NSAlert is to static / inflexible to achieve our goal (see RelinkDialog, Unlink).
#  - We want to show a dialog from an async widget callback: this currently causes trouble
#    with Toga's handling of the event loop.
#  - We want to keep the event loop running while showing the dialog *and* we cannot
#    use an NSAlert as sheet.


class Dialog(Window):
    """A generic dialog following cocoa's NSAlert style."""

    WINDOW_WIDTH = 420
    WINDOW_MIN_HEIGHT = 150

    PADDING_TOP = 18
    PADDING_BOTTOM = 18
    PADDING_LEFT = 25
    PADDING_RIGHT = 20
    TITLE_PADDING_BOTTOM = 12

    ICON_SIZE = (60, 60)
    ICON_PADDING_RIGHT = 20

    CONTENT_WIDTH = (WINDOW_WIDTH - PADDING_LEFT - PADDING_RIGHT
                     - ICON_PADDING_RIGHT - ICON_SIZE[0])

    def __init__(self, title='Alert', message='', button_labels=('Ok',), default='Ok',
                 accessory_view=None, icon=None, callback=None, app=None):
        super().__init__(
            resizeable=False, closeable=False, minimizable=False, title=' ',
            is_dialog=True, app=app
        )

        if not callback:
            def callback(sender):
                self.close()

        self.resizeable = True
        self.size = (self.WINDOW_WIDTH, self.WINDOW_MIN_HEIGHT)

        if not icon:
            if self.app:
                icon = self.app.icon
            else:
                icon = toga.Icon('')

        self.msg_title = Label(
            text=title,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=self.TITLE_PADDING_BOTTOM,
                font_weight=BOLD,
                font_size=13
            ),
        )
        self.image = toga.ImageView(
            icon,
            style=Pack(
                width=self.ICON_SIZE[0],
                height=self.ICON_SIZE[1],
                padding_right=self.ICON_PADDING_RIGHT
            )
        )
        self.msg_content = Label(
            text=message,
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=10, font_size=11, flex=1)
        )
        self.spinner = toga.ActivityIndicator(style=Pack(width=16, height=16))
        self.dialog_buttons = DialogButtons(
            labels=button_labels,
            default=default,
            on_press=callback,
            style=Pack(width=self.CONTENT_WIDTH, padding=0, alignment=CENTER)
        )
        self.dialog_buttons.children.insert(0, self.spinner)

        self.accessory_view = accessory_view or toga.Box()

        self.content_box = toga.Box(
            children=[
                self.msg_title,
                self.msg_content,
                self.accessory_view,
                self.dialog_buttons,
            ],
            style=Pack(direction=COLUMN)
        )

        self.outer_box = toga.Box(
            children=[self.image, self.content_box],
            style=Pack(
                direction=ROW,
                padding=(
                    self.PADDING_TOP, self.PADDING_RIGHT,
                    self.PADDING_BOTTOM, self.PADDING_LEFT
                )
            )
        )

        clear_background(self.outer_box)

        self.content = VibrantBox(
            children=[self.outer_box],
            material=VisualEffectMaterial.WindowBackground
        )
        self.center()

    def show_as_sheet(self, window):
        self.content.material = VisualEffectMaterial.Sheet
        super().show_as_sheet(window)

    def show(self):
        self.content.material = VisualEffectMaterial.WindowBackground
        super().show()


class ProgressDialog(Dialog):
    """A dialog to show progress."""

    def __init__(self, msg_title='Progress', icon=None, callback=None, app=None):

        self.progress_bar = toga.ProgressBar(
            max=0,
            style=Pack(width=self.CONTENT_WIDTH, padding=(0, 0, 10, 0))
        )
        self.progress_bar.start()

        super().__init__(
            title=msg_title, button_labels=('Cancel',), icon=icon,
            callback=callback, accessory_view=self.progress_bar, app=app
        )

        # this is hackish but works as long as the window has not yet been shown
        self.content_box._children.remove(self.msg_content)


class DetailedDialog(Dialog):
    """A generic dialog following cocoa NSAlert style, including a scroll view to
    display detailed text."""

    WINDOW_WIDTH = 650
    WINDOW_MIN_HEIGHT = 400

    CONTENT_WIDTH = (WINDOW_WIDTH - Dialog.PADDING_LEFT - Dialog.PADDING_RIGHT
                     - Dialog.ICON_PADDING_RIGHT - Dialog.ICON_SIZE[0])

    def __init__(self, title='Alert', message='', button_labels=('Ok',), default='Ok',
                 icon=None, callback=None, details_title='Traceback', details='', app=None):

        label = Label(
            details_title,
            style=Pack(
                width=self.CONTENT_WIDTH,
                padding_bottom=10,
                font_size=12, font_weight=BOLD
            )
        )
        clear_background(label)

        text_view_height = self.WINDOW_MIN_HEIGHT - Dialog.WINDOW_MIN_HEIGHT - 15
        text_view = RichMultilineTextInput(
            details,
            readonly=True,
            style=Pack(width=self.CONTENT_WIDTH, height=text_view_height, padding_bottom=15)
        )
        accessory_view = toga.Box(
            children=[label, text_view],
            style=Pack(direction=COLUMN)
        )

        super().__init__(
            title=title, message=message, button_labels=button_labels,
            default=default, icon=icon, callback=callback, accessory_view=accessory_view,
            app=app
        )


class UpdateDialog(Dialog):
    """A dialog to show available updates with release notes."""

    WINDOW_WIDTH = 700
    WINDOW_MIN_HEIGHT = 400

    CONTENT_WIDTH = (WINDOW_WIDTH - Dialog.PADDING_LEFT - Dialog.PADDING_RIGHT
                     - Dialog.ICON_PADDING_RIGHT - Dialog.ICON_SIZE[0])

    def __init__(self, version='', release_notes='', icon=None, app=None):

        link_button = FollowLinkButton(
            label='GitHub Releases',
            url=__url__ + '/releases',
            style=Pack(padding_bottom=10),
        )

        label = Label(
            'Release Notes',
            style=Pack(
                width=self.CONTENT_WIDTH, padding_bottom=10,
                font_size=12, font_weight=BOLD
            )
        )
        clear_background(label)

        html_notes = markdown2.markdown(release_notes)
        html_notes = html_notes.replace('<h4>', '<br/> <h4>')
        html_notes = html_notes.replace('<h3>', '<br/> <h3>')

        text_view_height = self.WINDOW_MIN_HEIGHT - Dialog.WINDOW_MIN_HEIGHT - 15
        text_view = RichMultilineTextInput(
            html=html_notes,
            readonly=True,
            style=Pack(width=self.CONTENT_WIDTH, height=text_view_height,
                       padding_bottom=15)
        )
        accessory_view = toga.Box(
            children=[link_button, label, text_view],
            style=Pack(direction=COLUMN)
        )

        message = (
            f'Maestral v{version} is available. Please use your package manager '
            f'to update or download the latest binary from GitHub.'
        )

        super().__init__(
            title='Update available', message=message, button_labels=('Ok',),
            icon=icon, accessory_view=accessory_view, app=app
        )
        self.msg_content.style.padding_bottom = 0
        self.msg_content.style.font_size = 12
        self.msg_content.style.height = 40


class RelinkDialog(Dialog):
    """A dialog to relink Maestral."""

    EXPIRED = 0
    REVOKED = 1

    VALID_MSG = 'Verified. Restarting Maestral...'
    INVALID_MSG = 'Invalid token'
    CONNECTION_ERR_MSG = 'Connection failed'

    LINK_BTN = 'Link'
    CANCEL_BTN = 'Cancel'
    UNLINK_BTN = 'Unlink and Quit'

    CONTENT_WIDTH = 325

    def __init__(self, app, reason):

        self.mdbx = app.mdbx
        self.reason = reason

        url = self.mdbx.get_auth_url()

        if self.reason == self.EXPIRED:
            reason = 'expired'
            title = 'Dropbox Access Expired'
        elif self.reason == self.REVOKED:
            reason = 'been revoked'
            title = 'Dropbox Access Revoked'
        else:
            raise ValueError(f'Invalid reason {self.reason}')

        msg = ('Your Dropbox access has {0}. To continue syncing, please retrieve a new '
               'authorization token from Dropbox and enter it below.').format(reason, url)

        self.website_button = FollowLinkButton(
            label='Retrieve Token', url=url, style=Pack(padding_bottom=10)
        )
        self.token_field = toga.TextInput(
            placeholder='Authorization token',
            on_change=self.token_field_validator,
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=20)
        )

        token_box = toga.Box(
            children=[
                self.website_button,
                self.token_field,
            ],
            style=Pack(direction=COLUMN,)
        )

        super().__init__(title=title, message=msg, accessory_view=token_box,
                         button_labels=(self.LINK_BTN, self.CANCEL_BTN, self.UNLINK_BTN),
                         callback=self.on_dialog_press, app=app)

        self.dialog_buttons[self.LINK_BTN].enabled = False

    def on_dialog_press(self, btn_name):

        for btn in self.dialog_buttons:
            btn.enabled = False

        self.token_field.enabled = False
        self.spinner.start()

        if btn_name == self.CANCEL_BTN:
            self.app.exit()
        elif btn_name == self.UNLINK_BTN:
            self.do_unlink()
        elif btn_name == self.LINK_BTN:
            self.do_relink()

    @async_call
    async def do_unlink(self):
        await run_maestral_async(self.mdbx.config_name, 'unlink')
        self.app.exit()

    @async_call
    async def do_relink(self):

        token = self.token_field.value
        res = await run_maestral_async(self.mdbx.config_name, 'link', token)

        self.spinner.stop()

        if res == 0:
            alert_sheet(
                window=self,
                title='Relink successful!',
                message='Click OK to restart.',
                callback=self.app.restart,
                icon=self.app.icon,
            )
        elif res == 1:
            alert_sheet(
                window=self,
                title='Invalid token',
                message='Please make sure you copy the correct token.',
                icon=self.app.icon,
            )
        elif res == 2:
            alert_sheet(
                window=self,
                title='Connection failed',
                message='Please check your internet connection.',
                icon=self.app.icon,
            )

        self.dialog_buttons[self.CANCEL_BTN].enabled = True
        self.dialog_buttons[self.UNLINK_BTN].enabled = True
        self.token_field.enabled = True

    def token_field_validator(self, widget):
        self.dialog_buttons[self.LINK_BTN].enabled = len(widget.value) > 10
