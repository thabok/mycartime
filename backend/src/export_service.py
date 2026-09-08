"""
Renders the frontend's isolated /export view in a headless browser and
screenshots it, for the "export plan as PNG" feature.

We drive the real frontend app (rather than re-implementing the table
markup/styling here) so the exported image always matches what the app
actually looks like. A real browser (Playwright/Chromium) is used instead of
a client-side canvas library so the screenshot is pixel-perfect - no
re-implemented text/SVG layout to get subtly wrong.
"""
import logging

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

CAPTURE_SELECTOR = '[data-export-capture="true"]'


class ChromiumNotAvailableError(Exception):
    """Raised when Playwright can't find a Chromium build to launch - e.g.
    the "lite" packaged build, which ships without one (see packaging/)."""


def render_week_screenshots(members, plan, reference_date, show_designated_driver,
                             show_solo_driver, dark_mode, frontend_origin):
    """
    Returns {'weekA': <png bytes>, 'weekB': <png bytes>}.

    `reference_date` is a "yyyy-MM-dd" string or None, mirroring the format
    the frontend itself stores in localStorage under 'carpool-reference-date'.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError as e:
            raise ChromiumNotAvailableError(
                "PNG export needs a Chromium browser, which isn't available in this build. "
                "Use the 'with Chromium' download, or run `playwright install chromium` if "
                "running from source."
            ) from e
        try:
            context = browser.new_context(device_scale_factor=2)
            page = context.new_page()

            # localStorage can only be written once we're on the target
            # origin, so land on it first, seed it, then navigate to the
            # actual export route for each week.
            page.goto(frontend_origin + '/export')
            page.evaluate(
                """(data) => {
                    localStorage.setItem('carpool-members', JSON.stringify(data.members));
                    localStorage.setItem('carpool-plan', JSON.stringify(data.plan));
                    localStorage.setItem('carpool-reference-date', JSON.stringify(data.referenceDate));
                    localStorage.setItem('carpool-show-designated-driver', JSON.stringify(data.showDesignatedDriver));
                    localStorage.setItem('carpool-show-solo-driver', JSON.stringify(data.showSoloDriver));
                    localStorage.setItem('carpool-theme-dark', JSON.stringify(data.darkMode));
                }""",
                {
                    'members': members,
                    'plan': plan,
                    'referenceDate': reference_date,
                    'showDesignatedDriver': show_designated_driver,
                    'showSoloDriver': show_solo_driver,
                    'darkMode': dark_mode,
                },
            )

            images = {}
            for image_key, week_param in (('weekA', 'A'), ('weekB', 'B')):
                page.goto(f'{frontend_origin}/export?week={week_param}')
                page.wait_for_load_state('networkidle')
                locator = page.locator(CAPTURE_SELECTOR)
                locator.wait_for(state='visible')
                images[image_key] = locator.screenshot()

            return images
        finally:
            browser.close()
