# hanshsieh-studio

Portfolio site for Hans Hsieh. GitHub Pages publishes the `main` branch.

## Link preview

LINE, Facebook, Messenger, iMessage, WhatsApp, and Slack read the preview from the page's meta tags. They do not run the page's JavaScript, so those tags are written in `index.html`.

The picture is the first photo of the newest Instagram post in `works.json` (the first item in `ig`). The site stores a JPEG about 1200 pixels wide, under 1 MB, in `og/`. The file name includes the post code and a short id, so a new photo is a new address and clients fetch it again.

Adding a post stays the same: upload the photos and update `works.json`. The Link preview action rebuilds `og/` and `index.html`, commits that result, and asks GitHub Pages to publish the commit. A commit made by the action does not start the action again. Keep the Pages source on **Deploy from a branch** (`main`, folder `/`). That is the publisher the action calls.

The public address is set in one place, `preview.config.json`:

```json
{
  "siteUrl": "https://kuannauk.github.io/hanshsieh-studio"
}
```

When `hanshsieh.studio` is connected, change `siteUrl` to `https://hanshsieh.studio` and push. Leave the CNAME file out until the domain is actually attached in the GitHub Pages settings.

### Refresh a cached thumbnail

The image address changes with the photo. LINE and Facebook still keep the old card until they read the page again.

- Facebook and Messenger: open [Sharing Debugger](https://developers.facebook.com/tools/debug/), paste the page URL, then choose Scrape Again.
- LINE: open [LINE Page Poker](https://poker.line.naver.jp/) and paste the same page URL.
- Slack: paste the link again after the page has been scraped.
- iMessage and WhatsApp: send the link again after the page has been scraped.

The page URL today is `https://kuannauk.github.io/hanshsieh-studio/`.
