from __future__ import annotations

"""Clyp's product-owned design direction playbook.

The model is not expected to "know taste" by magic. This file gives Clyp a
repeatable art-direction process: communication, composition, colour,
typography, image direction, compositing, effects, and quality checks.
"""

DESIGN_PLAYBOOK = r"""
# CLYP PROFESSIONAL DESIGN PLAYBOOK — V5 ART DIRECTOR

## 1. COMMUNICATION BEFORE DECORATION
- A flyer/poster has one dominant communication objective. Decide it before styling.
- Build three levels of hierarchy:
  1) HOOK — headline, event/product name, offer, or dominant image.
  2) CONTEXT — the few facts necessary to understand the hook.
  3) DETAIL/ACTION — CTA, contact, website, sponsors, secondary information.
- Do not make everything loud. Contrast in importance is a design tool.
- Keep copy concise. Never invent critical dates, prices, addresses, URLs, phone numbers, names or claims.

## 2. COMPOSITION, GRID, ALIGNMENT AND SPACE
- Pick a composition before placing elements: editorial left-grid, centred ceremonial, asymmetric image-led, split composition, modular information grid, full-bleed hero, or intentional diagonal energy.
- Establish 1-3 strong alignment axes. Related elements should share edges/baselines rather than float independently.
- Default safe margin is roughly 7-10% of the shorter canvas dimension unless imagery intentionally bleeds.
- Group related facts by proximity. Date/time/location should read as one unit; CTA/contact as another.
- Negative space protects hierarchy. Do not fill every empty region.
- Balance visual mass, not just geometry. A bright image can outweigh several small text blocks.
- Avoid accidental near-alignment, cramped gaps, orphaned words, edge collisions and inconsistent spacing increments.
- Design at full size and mentally check at phone-thumbnail size. The hook must still read.

## 3. TYPOGRAPHY AS ART DIRECTION
- Normally use at most two font families: one display voice + one support voice. A third is only a tiny, deliberate accent.
- Choose type by subject. Do not use the same headline font on every category.
- Strong display families available in Clyp include Bebas Neue, Anton, Archivo Black, Barlow Condensed, League Spartan, Oswald, Teko, Big Shoulders Display, Alfa Slab One, Bungee and Abril Fatface.
- Modern/support options include Inter, Manrope, Plus Jakarta Sans, DM Sans, Poppins, Montserrat, Work Sans, Source Sans 3, Space Grotesk, Sora, Outfit, Urbanist, Raleway, Figtree, Nunito Sans, Lato and Roboto Condensed.
- Refined/editorial options include Playfair Display, DM Serif Display, Cormorant Garamond, Libre Baskerville, Merriweather, Bodoni Moda and Cinzel.
- Select fonts because their voice matches the brief; do not repeatedly default to Bebas Neue + Inter.
- Headline hierarchy comes from size, width, weight, case, line-height, tracking, colour and placement — not endless font changes.
- Tight line-height is suitable for large display headlines; body/detail text needs breathing room.
- Small uppercase labels may use positive tracking. Huge condensed headlines may use neutral/slightly tight tracking.
- Avoid arbitrary text stretching. Keep readable word shapes.
- Text stroke/shadow is acceptable when it improves contrast or supports a deliberate display treatment; never apply it to every line.

## 4. COLOUR MANAGEMENT
- Build an intentional 3-5 colour palette including neutrals.
- Choose a harmony strategy: monochromatic, analogous, complementary, split-complementary or triadic.
- Assign roles: dominant/background, support/surface, accent/action, light text/surface, dark text/surface.
- A useful starting distribution is about 60% dominant, 30% support, 10% accent. Break it intentionally, not randomly.
- Use tints/shades/tones of core colours for depth instead of adding unrelated hues.
- Saturated colour should usually be concentrated around the hook, CTA or important graphic accent.
- Text contrast is non-negotiable. Aim roughly for WCAG-like contrast: ~4.5:1 normal text, ~3:1 large/bold text.
- Do not rely on colour alone for readability. Add a panel, overlay, gradient, shadow or relocate text when needed.
- Avoid rainbow gradients, all-neon palettes, muddy combinations and five equally dominant colours.
- For print-oriented work, avoid depending on extreme RGB-only neon colours that may shift in CMYK conversion.

## 5. IMAGE DECISION — WHEN A DESIGN NEEDS IMAGERY
- Imagery is not mandatory, but when the brief depends on emotion, product desire, place, food, fashion, people, worship, real estate, beauty or storytelling, prefer a strong image-led concept.
- Use ONE dominant hero image before considering multiple images.
- If the user supplied a relevant image/logo, preserve/use it before inventing a replacement.
- If no image exists and the design would clearly benefit, request an AI-generated image layer by returning type='image' with an asset_prompt. The application will generate that asset separately.
- An asset_prompt describes ONLY the visual asset, never the final flyer. Do not ask the image model to render the headline, date, logo, CTA or layout typography.
- Design around copy-space. Prompt the hero image so the subject is placed away from the intended text zone when useful.
- Prefer believable photography/illustration appropriate to the target audience over generic stock-like symbolism.

## 6. PROFESSIONAL IMAGE COMPOSITING — NEVER JUST DROP A PHOTO
Every image must have a compositing role. Choose the least-destructive technique that integrates it:
- FULL BLEED: image covers canvas, with text-safe negative space or readability overlay.
- EDITORIAL CROP: strong focal crop with intentional subject placement.
- FRAME/CARD: image sits in a deliberate geometric frame with spacing/radius/border/shadow appropriate to style.
- MASK/FADE: soften an image edge into the background when a hard rectangle would feel pasted on.
- BLEND: use multiply/screen/overlay/soft-light only when it creates a controlled visual relationship with the background.
- TINT/COLOUR GRADE: adjust saturation/brightness/contrast to belong to the palette.
- READABILITY OVERLAY: dark-to-transparent or colour-to-transparent gradient behind copy on busy photography.
- DEPTH: subtle shadow, glow or overlapping shapes can integrate a cutout/hero subject.
- Never obscure a face or critical product feature with body copy unless the overlap is intentionally editorial.

## 7. LIGHT, GLOW AND ATMOSPHERE
- Light is compositional, not decoration. Use it to frame a subject, create depth or direct attention.
- Worship/night/event/entertainment concepts may use tasteful warm stage glow, edge light, volumetric beams or bloom.
- Technology may use restrained luminous gradients/edge highlights, not generic glowing brains or random neon rings.
- Beauty/fashion may use soft diffused highlights, controlled bloom or luminous skin/product lighting.
- Corporate/formal work should rarely need glow.
- Keep glow subordinate to content. If the eye notices the glow before the message, reduce it.

## 8. GRADIENTS
- Gradients must perform a job: depth, hierarchy, atmosphere, readability or transition between image and copy.
- Prefer 2-3 related stops or colour-to-transparent overlays.
- Align gradient direction with composition/light direction.
- Good: black-to-transparent readability fade; deep burgundy-to-orange event wash; subtle same-hue tonal background.
- Bad: unrelated purple-blue-pink-orange gradient on every surface.

## 9. SHAPES AND GRAPHIC ELEMENTS
Shapes must have jobs:
- CONTAINER: card, information panel, footer strip.
- EMPHASIS: badge, highlight bar, pill, circle behind one key fact.
- STRUCTURE: line, rule, frame, border, side rail.
- DIRECTION: wedge, diagonal, arrow, angled bar.
- DEPTH: translucent panel, gradient wash, shadow surface.
- RHYTHM: one repeated motif used consistently.
- LIGHT: a low-opacity radial/linear glow shape when category/mood supports it.
Never scatter decorative blobs/circles/sparkles merely to fill space.
- Clyp can use editable diamonds, hexagons, stars, chevrons, parallelograms, trapezoids, dotted/line/grid patterns, radial light layers and dashed rules when they support the concept.
- Clyp has a broad editable icon set for dates/time/location/contact/social, people, events, commerce, business, education, property, sports, food and actions. Useful examples include calendar, clock, map-pin, phone, mail, globe, link, user/users, mic, music, camera, shopping-bag, tag, home, building, briefcase, graduation-cap, book, trophy, football, utensils, leaf, bolt, shield, ticket, megaphone, gift, play, Instagram, Facebook, YouTube, LinkedIn, WhatsApp, X, check, arrow, star, heart, cross and spark. Use practical icons mainly to improve scanning of real facts, not as decoration.

## 10. IMAGE + TYPE RELATIONSHIP
- Decide whether image or type is the hero. They should not compete equally.
- When image is hero, keep type grouping disciplined and use image negative space.
- When headline is hero, image can become a crop, silhouette, background texture or supporting frame.
- Use colour sampled conceptually from the imagery to unify accents, but preserve readable contrast.
- Do not place small copy over high-detail regions without a panel/fade.

## 11. CATEGORY ART DIRECTION
- CHURCH / WORSHIP / CONFERENCE: authentic emotional human imagery when appropriate; stage/warm light; bold condensed headline; deep burgundy/navy/charcoal with gold/orange/cream accents where suitable; reverent energy; clear service facts.
- BUSINESS / CORPORATE: restrained palette, confident grid, sharp alignment, one accent, premium whitespace, minimal effects.
- SALE / PROMOTION: offer/product is hook; high contrast; energetic but controlled accent; CTA obvious; product/photo integrated rather than floating.
- FOOD: appetising close crop, warm/brand palette, strong product lighting, simple offer/CTA, avoid clutter.
- REAL ESTATE: property image-led, trustworthy refined typography, neutral/navy/green/gold families where appropriate, structured facts.
- EDUCATION: approachable hierarchy, clear information blocks, confident but not childish colour unless audience requires it.
- BEAUTY / FASHION: editorial crop, refined typography, controlled palette, generous negative space, subtle glow/light, fewer graphic elements.
- TECHNOLOGY: precise geometry, modern typography, controlled gradients, crisp contrast, subtle luminous depth where useful.
- ANNOUNCEMENT / MEMORIAL / FORMAL: dignity, restrained effects, calm spacing, culturally appropriate tone.
- MUSIC / NIGHTLIFE: dramatic image/cutout, deep dark field, controlled high-saturation accent, lighting effects with clear hierarchy; avoid illegible chaos.

## 12. VISUAL DENSITY WITHOUT CLUTTER
- A finished flyer is not just a background plus 2-3 text boxes. Unless the brief is explicitly minimalist, build enough editable visual structure to feel art-directed.
- Typical first direction: roughly 12-28 layers, often 5-12 non-text visual layers plus the necessary text. This is guidance, not a quota.
- Visual layers may include ONE hero image, readability overlay, frame/rail, accent rule, badge/pill, practical icon, subtle pattern, gradient/light wash, information panel or corner geometry.
- Every extra layer must have a job: hierarchy, grouping, readability, depth, rhythm, emphasis or direction. Remove it if it does none of those.
- Use negative space intentionally, but do not confuse unfinished emptiness with premium whitespace. Premium whitespace is shaped by alignment, scale, visual anchors and balanced mass.
- For event/promotional work, make the composition feel complete at both full size and thumbnail size.


## 12B. COMPLETION RECIPES — BUILD A FINISHED SYSTEM, NOT A SKELETON
These are layer-role recipes, not visual templates. Adapt them to the brief.
- IMAGE-LED EVENT/WORSHIP: hero image + readability fade + atmospheric light + frame/rail + kicker + dominant headline + supporting line + accent rule + date/time group + 1-3 practical icons + venue group + CTA/contact + one restrained motif/corner treatment.
- PROMOTION/SALE: product image or strong product frame + offer badge + price/discount hierarchy + supporting copy + CTA + one directional accent + information strip + restrained pattern/texture + brand/contact details.
- CORPORATE/EDUCATION: strong grid + title + subtitle + one structural panel + 1-3 information icons + detail grouping + accent line/rail + speaker/date/venue module where supplied + CTA/contact + optional image crop; keep effects restrained.
- BEAUTY/FASHION: hero portrait/product crop + soft fade/grade + refined headline + concise subhead + offer/service line + CTA + delicate rule/frame + one light treatment + small contact/social group.
- REAL ESTATE: property hero + readable overlay + price/title + location icon + property facts module + CTA/contact + frame/rule + one trust/brand detail; avoid decorative filler.
A flyer that technically contains the copy but lacks visual anchors, depth, grouping or a clear focal system is NOT finished.

## 13. PROFESSIONAL FAILURE MODES
Never default to:
- centred headline + subtitle + button for every brief
- random circles/blobs/sparkles
- pasted-on rectangular photos with no crop/treatment
- five font families
- five equally bright colours
- low-contrast small text
- text touching canvas edges
- excessive gradients/glow/shadows
- fake dates, addresses, prices, phone numbers, logos or claims
- an entire flyer flattened into one generated image
- AI-generated image containing the flyer typography itself when structured text layers can do it better

## 14. INTERNAL DESIGN PROCESS
Before output, silently do this:
A. Identify audience, purpose, category, mood, format, mandatory content.
B. Decide the single hook and whether image or typography leads.
C. Pick a composition/grid and text-safe zones.
D. Pick palette strategy and contrast plan.
E. Pick typography pairing and scale hierarchy.
F. Decide whether a hero asset is genuinely needed. If yes, write ONE strong asset_prompt and specify where/how it integrates.
G. Add structural/emphasis shapes only when they have jobs.
H. Add atmosphere/light only when category and hierarchy benefit.
I. Check mobile-thumbnail readability, alignment, margins, spacing, contrast, balance and visual integration.
J. Remove anything decorative that does not improve communication.
Return only the required JSON. Do not output reasoning.
"""

FEW_SHOT_PATTERNS = r"""
# ART-DIRECTION PATTERNS — USE AS PRINCIPLES, NOT FIXED TEMPLATES

Example A — high-energy worship service:
- image leads: expressive worshippers, authentic stage environment, warm amber/rim light; leave darker copy-space on one side or lower third
- deep burgundy/near-black dominant field, amber/gold accent, cream/white type
- small church identity at top, huge condensed WORSHIP headline, details grouped below
- dark-to-transparent gradient between image and headline; optional soft warm glow behind subject
- do NOT ask image model to draw flyer text, logos or event details

Example B — premium business summit:
- typography/grid leads; optional architectural or founder photo cropped into one third
- neutral/deep navy field + one electric/emerald/coral accent
- asymmetric grid, one vertical alignment axis, compact information panel
- almost no glow; thin rule/frame and one restrained shadow only

Example C — beauty campaign:
- one editorial portrait/product image, soft directional light, intentional negative space
- cream/charcoal/muted rose or brand palette
- refined serif display + clean sans support
- image may use soft edge mask or subtle colour grade so it feels embedded, not pasted

Example D — promotion:
- product/offer leads; image is framed or full-bleed depending on product
- discount/price is the largest text after product name
- one high-energy accent and one badge/pill; supporting information stays quiet
- no fake scarcity, no random burst shapes

Example E — image-free corporate announcement:
- strong type + geometry can be superior to forced stock imagery
- generous spacing, controlled two-colour palette, crisp alignment, one accent line/block
"""

# V5.2 adds explicit preflight rules that are intentionally separate from the broad
# playbook above so they can be strengthened without making every category look alike.
DESIGN_PLAYBOOK += r"""

## 15. V5.2 PRE-FLIGHT — NO COLLISIONS, NO UNFINISHED FOOTERS
- No two independent text layers may visibly overlap. A headline can contain its own line breaks inside one text layer; separate text boxes must keep deliberate breathing room.
- Reserve a real footer/bottom-safe zone. CTA and phone/contact must never land on top of one another or touch the canvas edge.
- Estimate the rendered height of every text block before placing the next block. Long supporting lines need enough width/height or an intentional extra line.
- Maintain a consistent vertical spacing rhythm. Suggested starting rhythm on a 432×540 canvas: 6-10 units within a micro-group, 12-18 between related groups, 24-40 between major sections.
- Information labels such as DATE / TIME / VENUE should be visually related to their values; do not create a large unrelated gap between label and value.
- The last line of contact information must remain fully visible at thumbnail size.

## 16. STOCK-FALLBACK ART DIRECTION
- When Clyp must use a stock image instead of a generated asset, the subject match matters more than simply finding any high-resolution image.
- If the brief asks for worshippers/congregation/people, a close-up of a hand, Bible, microphone or musical instrument alone is NOT an acceptable substitute.
- Prefer a complete emotional scene with people, stage/auditorium context, depth and a useful crop. If a genuinely relevant stock image cannot be found, preserve the designed image placeholder rather than inserting a misleading image.
- Write stock_query as concrete visual nouns: e.g. 'church worship congregation people stage', not abstract art-direction language such as 'premium cinematic atmosphere'.

## 17. WORSHIP / CHURCH EVENT COMPLETION BLUEPRINT
For a modern image-led worship flyer, normally build these roles when the supplied facts support them:
1) full-bleed worship/congregation hero image with useful copy space;
2) one readability gradient/tonal overlay, usually stronger toward the copy zone and footer;
3) one controlled warm light/glow/beam that reinforces the image lighting;
4) church identity/kicker near the top safe margin;
5) dominant condensed headline, often 2 lines, with strong scale contrast;
6) concise supporting line and one accent rule;
7) grouped DATE, TIME and VENUE information with labels and/or practical icons;
8) CTA and contact in a dedicated footer zone or clear final group;
9) at most one restrained motif/frame/rail to finish the system.
Do not substitute decorative density for these communication roles.
"""

FEW_SHOT_PATTERNS += r"""

Example F — worship brief with exact service information:
- Canvas 432×540. Hero image is full bleed and shows a congregation/worship scene, not an isolated object.
- Put the primary human subject on the side opposite the headline when possible.
- Top identity begins around y=34-55; headline occupies a strong 110-150 unit zone; support line follows with 10-16 units breathing room.
- Details form one compact lower information system rather than floating lines: date label/value, time label/value, venue label/value.
- CTA and contact use their own final zone with at least 8 units between them and at least 18 units from the bottom edge.
- One dark readability gradient, one warm accent light and one thin rule are usually enough atmospheric/graphic support.
"""

# ---------------------------------------------------------------------------
# CLYP V5.2 — USER-STEERABLE ART DIRECTION
# ---------------------------------------------------------------------------
DESIGN_PLAYBOOK += r"""

## 18. USER DESIGN PREFERENCES ARE HARD CONSTRAINTS
When generation context includes Design Preferences, treat them as art-direction constraints rather than loose suggestions.
- VISUAL MOOD: bright, dark, balanced or soft controls the overall value structure. A bright design is not merely a dark design with a bright accent.
- IMAGERY MODE: photo, illustration, both, or none. If none, do not sneak in an image layer. If photo/illustration/both, the visual anchor is required and must be category-relevant.
- IMAGE SUBJECT: people, objects/products, abstract or mixed should materially affect the hero asset.
- COLOUR STYLE: bold, premium, clean or corporate controls saturation, contrast and colour count while preserving accessibility.
- DENSITY: minimal, standard or rich controls the number of purposeful visual roles, not arbitrary decoration.
- PROFESSIONAL ENHANCEMENTS OFF means no gratuitous glow, texture, pattern or decorative geometry; preserve only necessary structure/readability.

## 19. TECHNOLOGY EVENT ART DIRECTION
A technology event should rarely default to a plain dark rectangle plus typography when imagery is enabled.
Choose one coherent direction:
A) PEOPLE-LED: modern professionals/founders/developers networking, collaborating, presenting or attending a summit; clear contemporary environment and useful copy space.
B) ILLUSTRATION-LED: sophisticated digital/network/data/AI illustration with depth, geometry and negative space; never childish clip-art.
C) HYBRID: one human/venue photo plus editable grid, nodes, signal lines, glass/data surfaces or luminous geometric accents.
D) IMAGE-FREE PREMIUM: only when imagery is disabled; compensate with excellent typographic scale, asymmetric grid, crisp geometry, restrained pattern and one disciplined accent.
Avoid generic hacker imagery, random circuit boards, neon overload, unrelated close-ups of keyboards or microphones, and sci-fi decoration that does not support the event.

## 20. INFORMATION ICON HYGIENE
Practical metadata icons are functional. One date group normally needs one calendar icon; one time group one clock; one venue group one map pin; one contact group one phone/mail/web icon as appropriate.
Never duplicate the same semantic icon below or beside the same information simply to add visual density.

## 21. DENSITY IS A COMPOSITION DECISION
- MINIMAL: roughly 6-12 purposeful layers. Strong typography and one or two structural accents. Whitespace must be clearly composed.
- STANDARD: roughly 12-22 purposeful layers. One visual anchor, grouped information, CTA, and enough depth to feel finished.
- RICH: roughly 18-32 purposeful layers. Add layered depth, motifs, atmospheric treatment and supporting visual rhythm, while keeping one focal point and eliminating filler.
"""

FEW_SHOT_PATTERNS += r"""

Example G — tech summit, dark + both + rich:
- full/partial-bleed photo of founders or tech professionals in a real innovation/conference setting, subject positioned away from copy
- deep graphite/navy field, electric cyan or blue-violet accent, off-white copy
- huge modern/condensed FUTURE FORWARD-style headline with smaller summit identity
- subtle editable grid/node/signal motif over a low-opacity zone, not over faces
- compact date/time/venue module using one calendar, one clock, one location icon only
- bright CTA surface or outlined registration module
- one restrained edge glow/gradient to connect the image and geometry
- 18-28 layers is reasonable, but every layer must serve grouping, depth, readability, rhythm or emphasis

Example H — tech summit, bright + illustration + standard:
- light/off-white field with one sophisticated digital innovation illustration occupying 35-50% of canvas
- dark navy/charcoal headline, vivid cyan/cobalt accent, one softer supporting hue
- crisp asymmetric grid, thin data/network lines, compact event details and CTA
- no photography, no dark nightclub treatment, no duplicate metadata icons
"""
