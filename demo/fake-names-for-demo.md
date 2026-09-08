# Fake names for manual demo screenshots

Paste the snippet below into the DevTools console on the app tab once. It
defines `toggleAnonymousMode()`, which flips between real and fake names
each time you call it — run it, take a screenshot, run it again to restore
real names before interacting further, and so on.

```js
function toggleAnonymousMode() {
  const FAKE_POOL = [
    ['Harry','Potter'],['Hermione','Granger'],['Ron','Weasley'],['Draco','Malfoy'],
    ['Neville','Longbottom'],['Luna','Lovegood'],['Cho','Chang'],['Seamus','Finnigan'],
    ['Dean','Thomas'],['Parvati','Patil'],['Lavender','Brown'],['Cedric','Diggory'],
    ['Fleur','Delacour'],['Viktor','Krum'],['Susan','Bones'],['Justin','Finch-Fletchley'],
    ['Terry','Boot'],['Michael','Corner'],['Angelina','Johnson'],['Oliver','Wood'],
  ];

  const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  // A single combined regex + lookup map, so every match in a piece of text
  // is found in one simultaneous scan - unlike applying each [from, to] pair
  // as its own sequential find/replace, which lets a later pair's `from`
  // accidentally match text a previous pair's `to` just produced (e.g. one
  // member's fake name landing inside another's), scrambling the result.
  // The (?<!...)/(?!...) lookarounds require a non-letter/non-digit on both
  // sides of the match, so e.g. a member named "Tim" only replaces the word
  // "Tim", not the "Tim" inside "Timetable". \p{L}/\p{N} (with the `u` flag)
  // cover accented letters too, so names like "Björn" still match correctly.
  const buildMatcher = (pairs) => {
    const map = new Map(pairs.filter(([from]) => from));
    const froms = [...map.keys()].sort((a, b) => b.length - a.length);
    if (froms.length === 0) return null;
    const alternation = froms.map(escapeRegExp).join('|');
    const regex = new RegExp(`(?<![\\p{L}\\p{N}])(?:${alternation})(?![\\p{L}\\p{N}])`, 'gu');
    return { map, regex };
  };

  const substitute = (matcher, text) => {
    if (!matcher) return null;
    let changed = false;
    const next = text.replace(matcher.regex, (match) => {
      changed = true;
      return matcher.map.get(match);
    });
    return changed ? next : null;
  };

  const applyToDom = (matcher) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    let node;
    while ((node = walker.nextNode())) textNodes.push(node);
    for (const textNode of textNodes) {
      const next = substitute(matcher, textNode.nodeValue);
      if (next !== null) textNode.nodeValue = next;
    }
    document.querySelectorAll('input, textarea').forEach((el) => {
      const next = substitute(matcher, el.value);
      if (next !== null) el.value = next;
    });
  };

  // Already anonymized -> revert using the mapping stashed from last time.
  if (window.__demoAnonReplacements) {
    const reverted = window.__demoAnonReplacements.map(([from, to]) => [to, from]);
    applyToDom(buildMatcher(reverted));
    delete window.__demoAnonReplacements;
    console.log('Reverted to real names.');
    return;
  }

  // Not anonymized -> build the fake identity mapping and apply it.
  const realMembers = JSON.parse(localStorage.getItem('carpool-members') || '[]');
  const used = new Set();
  const initialsFor = (first, last) => {
    const base = (first[0] + last[0]).toUpperCase();
    let candidate = base, n = 1;
    while (used.has(candidate)) candidate = base + (n++);
    used.add(candidate);
    return candidate;
  };
  const sorted = [...realMembers].sort((a, b) => (a.firstName + a.lastName).localeCompare(b.firstName + b.lastName));
  const identities = sorted.map((m, idx) => {
    const [fakeFirst, fakeLast] = FAKE_POOL[idx % FAKE_POOL.length];
    return {
      realFirst: m.firstName, realLast: m.lastName, realInitials: m.initials,
      fakeFirst, fakeLast, fakeInitials: initialsFor(fakeFirst, fakeLast),
    };
  });

  const replacements = [];
  for (const id of identities) {
    if (id.realLast) replacements.push([id.realLast, id.fakeLast]);
    if (id.realFirst) replacements.push([id.realFirst, id.fakeFirst]);
    replacements.push([id.realInitials, id.fakeInitials]);
  }

  applyToDom(buildMatcher(replacements));
  window.__demoAnonReplacements = replacements;
  console.log(`Anonymized ${identities.length} members. Call toggleAnonymousMode() again to revert.`);
}
```

## Usage

1. Paste the snippet above into the console once (per page load — it's lost on refresh, just re-paste it).
2. Call `toggleAnonymousMode()` → fake names appear → take your screenshot.
3. Call `toggleAnonymousMode()` again → real names are restored before you interact further.

Don't leave fake mode applied while interacting with the app: matching
requires whole-word boundaries (so e.g. a member named "Tim" won't touch
"Timetable"), but a real first name that's also a standalone English word
used elsewhere in the UI could still coincidentally match and get reverted
along with everything else once you toggle back.

## Notes

- Only touches DOM that's currently rendered (open dialogs, current tab). If
  you open a new dialog or navigate while in fake mode, toggle back to real,
  navigate, then toggle to fake again for the next screenshot.
- If two real members happen to share the same first name, both get mapped
  to the same fake first name (the lookup is keyed by the real string, so it
  can only hold one target per name) - a cosmetic limitation, not a leak.
- The WebUntis username field isn't a member, so it isn't covered. To mask it
  for a login screenshot: `document.querySelector('#username').value = 'demo.user'`,
  then restore it afterward (or just retype it once you're done
  screenshotting).
- The mapping is deterministic (alphabetical by real first+last name → pool
  order), so toggling to fake mode again after a page reload reproduces the
  same fake names each time.
