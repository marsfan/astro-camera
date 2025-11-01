#!/usr/bin/env python3
"""Page for displaying the images that have been taken."""
import asyncio
from base64 import b64encode
from functools import lru_cache
from pathlib import Path

import cv2
import simplejpeg
from nicegui import events, run, ui
from nicegui.events import ClickEventArguments, Handler

# Making this function a LRU cache means that we cache
# the images, so if another request is made, we already have scaled
# images in memory.


@lru_cache
def create_b64_thumb(image: Path) -> str:
    """Create a thumbnail with a maximum width of 350 pixels.

    Arguments:
        image: The image to create a thumbnail of

    Returns:
        base64 encoded image scaled to have a maximum width of 350 pixels.

    """
    # Load image as quickly as possible
    # Format needs to be BGR since that's what OpenCV uses
    im = simplejpeg.decode_jpeg(
        image.read_bytes(),
        colorspace="bgr",
        fastdct=True,
        fastupsample=True,
    )

    # Scale image to never be wider than 300px
    # FIXME: Extra check to ensure never taller than 200px?
    aspect = im.shape[1] / im.shape[0]
    if aspect > 1:
        aspect = 1/aspect
    im = cv2.resize(
        im,
        (350, int(350 * aspect)),
        interpolation=cv2.INTER_LINEAR,
    )

    # Encode rescaled image to bytes as fast as possible
    buf = b64encode(simplejpeg.encode_jpeg(im, colorspace="bgr", fastdct=True))
    # Return b64 encoding of the image.
    return f"data:image/jpeg;base64,{buf.decode('ascii')}"


def prep_elem(elem: ui.image, path: Path) -> tuple[ui.image, str]:
    """Create thumbnail version of an image, and get it in base64 encoding.

    The reason to also take in a ui.image element is so that we can
    keep track of which image belongs to which UI element. Since this
    function is called in parallel threads, keeping track of this
    relationship is needed, or thumbnails could be added to the wrong
    element.

    Arguments:
        elem: The UI element that the thumbnail should be added to
        path: Path to the image to create the thumbnail for on the disk.

    Returns:
        Two element tuple. The first element is the ui element that was
        passed in. The second element is the base64 encoded thumbnail
        for the image.

    """
    return elem, create_b64_thumb(path)


class NavButton(ui.button):
    """Buttons for moving forward and backwards through the images."""

    def __init__(
            self,
            icon: str,
            on_click: Handler[ClickEventArguments],
            stretch: bool,
    ) -> None:
        """Initialize navigation button.

        Arguments:
            icon: The icon to display for the button
            on_click: The function to call when the button is pressed.
            stretch: Whether or not to stretch the button vertically.

        """
        super().__init__(icon=icon, on_click=on_click)
        self.props("color=clear")
        if stretch:
            self.classes("h-full")


class DeleteDialog(ui.dialog):
    """Dialog to prompt for deleting an image."""

    def __init__(self, filepath: Path, card: ui.card) -> None:
        """Prompt the user to delete the specified image.

        Arguments:
            filepath: Path to delete. This should be the path to
                a single file, or a stem. All files with the matching
                stem (i.e. without extension), in the directory will
                be downloaded to the user.
            card: The card for the file to delete. If the user approves
                deleting the file, the card will be removed.

        """
        super().__init__(value=True)
        self._filepath = filepath
        self._card = card
        with self, ui.card():
            ui.label("Are you sure?")
            with ui.row():
                ui.button("Yes", on_click=self._delete_files)
                ui.button("No", on_click=self._close_dialog)

    def _close_dialog(self) -> None:
        """Don't delete, just close the dialog."""
        self.close()
        self.clear()

    def _delete_files(self) -> None:
        """Delete files and then close the dialog."""
        for file in self._filepath.parent.glob(f"{self._filepath.stem}.*"):
            file.unlink()
        self._close_dialog()
        self._card.clear()
        self._card.delete()


class Lightbox:
    """Main lightbox that displays the images."""

    def __init__(self) -> None:
        """Initialize the lightbox."""
        ui.colors(clear="#00000000")
        with ui.dialog().props("maximized").classes("bg-black") as self.dialog:
            ui.keyboard(self._handle_key)
            with ui.row(wrap=False, align_items="center"):
                NavButton("chevron_left", self._previous_image, True)
                self.large_image = ui.image().props("no-spinner fit=scale-down")
                with ui.column(align_items="stretch").classes("h-full"):
                    NavButton("close", self.dialog.close, False)
                    NavButton("chevron_right", self._next_image, True)

        self.image_list: list[Path] = []
        self.thumb_objs: list[ui.image] = []

    def add_image(self, im_path: Path) -> None:
        """Create the thumbnail objects, but don't fill with images yet."""
        self.image_list.append(im_path)
        with ui.card() as card:
            with ui.button(on_click=lambda: self._open(im_path)).props("flat dense square"):
                self.thumb_objs.append(
                    ui.image().classes("w-[350px] h-[200px]"),
                )
            # FIXME: Figure out how to center the text
            ui.label(text=im_path.stem)
            with ui.row(wrap=False).classes("w-full justify-center"):
                # FIXME: Implement metadata display
                ui.button(icon="info").tooltip("Metadata")
                ui.button(
                    icon="delete",
                    on_click=lambda: DeleteDialog(im_path, card),
                ).tooltip("Delete")
                ui.button(
                    icon="download",
                    on_click=lambda: self._download_files(im_path),
                ).tooltip("Download")

    async def populate(self) -> None:
        """Populate the thumbnails with the actual images."""
        # Zip pairs of the elements and the images of the thumbnails we
        # want.
        pairs = zip(self.thumb_objs, self.image_list, strict=True)

        # Create coroutines for setting each image thumbnail, then run
        # all of them at once.
        #
        # Even though this is computationally expensive, the logic is
        # all done in native code, not pure python. Native code can release
        # the GIL, so we can use io_bound (which uses a threadpoolexecutor)
        # to run all the jobs
        results = await asyncio.gather(
            *(run.io_bound(prep_elem, e, i) for e, i in pairs),
        )
        # Use the results from the coroutines to populate the elements.
        # We have to do this here, for thread safety reason
        #
        # FIXME: FIgure out how to execute these as the tasks are completed
        # so we don't need to wait for all thumbnails to be processed before
        # showuing them
        for element, image in results:
            element.set_source(image)

    def _handle_key(self, event_args: events.KeyEventArguments) -> None:
        """Handle user keypresses.

        Arguments:
            event_args: The arguments from the key press events.

        """
        if not event_args.action.keydown:
            return
        if event_args.key.escape:
            self.dialog.close()
        if event_args.key.arrow_left:
            self._previous_image()
        if event_args.key.arrow_right:
            self._next_image()

    def _next_image(self) -> None:
        """Navigate to the next image, if there is one."""
        index = self.image_list.index(self.large_image.source)
        if index < (len(self.image_list) - 1):
            self._open(self.image_list[index + 1])

    def _previous_image(self) -> None:
        """Navigate to the previous image, if there is one."""
        index = self.image_list.index(self.large_image.source)
        if index > 0:
            self._open(self.image_list[index - 1])

    def _open(self, filepath: Path) -> None:
        """Open the given image to the full sized dialog.

        Arguments:
            filepath: Path to the image to dispaly as full screen

        """
        self.large_image.set_source(filepath)
        self.dialog.open()

    def _download_files(self, filepath: Path) -> None:
        """Download files for an image to the user.

        Arguments:
            filepath: Path to download. This should be the path to
                a single file, or a stem. All files with the matching
                stem (i.e. without extension), in the directory will
                be downloaded to the user.

        """
        # FIXME: Do we want to compress all into a zip first?
        for file in filepath.parent.glob(f"{filepath.stem}.*"):
            ui.download(file)
