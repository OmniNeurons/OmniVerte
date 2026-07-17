# file: ui/settings_pages/custom_style_templates.py

"""
Profession-specific starting points for the Custom rewrite style.

Each template fills the Custom style page's two fields: the name resolved from
``name_key`` goes into ``CUSTOM_STYLE_NAME`` (the Custom button's tooltip) and
``prompt`` into ``CUSTOM_STYLE_PROMPT`` (fed verbatim to the model by
``rewrite_text`` in ``services/text_operations.py``).

The two halves sit on opposite sides of the chrome/data line, which is why one
is translated and the other is not:

* ``name_key`` is a **catalog key**, resolved by the page when it builds the
  button (never here — see the ``i18n`` package docstring's freeze rule). The
  name is a label, so it follows the UI locale.
* ``prompt`` is **model input, and stays English on purpose.** It is not shown
  as chrome; it is a system-level instruction, and its English siblings
  (``CONVERSATIONAL_STYLE`` / ``BUSINESS_STYLE``, and the preservation wrapper
  ``rewrite_text`` puts around every style) are what it has to sit beside in one
  prompt. Translating only these ten would make them the sole exception and put
  a hybrid system message in front of the model for no gain: the wrapper already
  pins the output language to the *speaker's*, so an English instruction rewrites
  Russian dictation into Russian. A translated name next to an English prompt is
  therefore deliberate, not an oversight.

The bodies assume the preservation rules that ``rewrite_text`` already wraps
around every style instruction — "Preserve the original meaning, language,
proper nouns, code identifiers, URLs, and inline code. Return ONLY the
rewritten text…" — so they do NOT repeat those rules or refer to a separate
"BASE" block.
"""

from __future__ import annotations

from typing import NamedTuple


class StyleTemplate(NamedTuple):
    emoji: str     # button-label prefix, e.g. "⚖️"
    name_key: str  # catalog key -> CUSTOM_STYLE_NAME, e.g. "…lawyer.name" (no emoji)
    prompt: str    # CUSTOM_STYLE_PROMPT body (English — see the module docstring)


CUSTOM_STYLE_TEMPLATES: list[StyleTemplate] = [
    StyleTemplate(
        "⚖️", "customstyle.templates.lawyer.name",
        "Audience: legal correspondence or internal legal work product.\n"
        "Infer the document type from the content (client letter, internal memo, demand letter,\n"
        "email to opposing counsel, file note, or billing narrative) and format accordingly.\n"
        "- Register: formal, precise, measured. Hedge where the speaker hedges; do not overstate.\n"
        "- Preserve defined terms, party names, dates, and figures verbatim.\n"
        "- Do NOT state legal conclusions, cite authority, or assert facts the speaker did not give.\n"
        "  Where authority or a citation is clearly needed but absent, mark [cite needed].\n"
        "- For a billing narrative: produce one concise, billable-style time entry describing the\n"
        "  work performed (no filler, no padding).\n"
        "- Structure longer pieces with a clear issue/position and logically ordered paragraphs.",
    ),
    StyleTemplate(
        "🩺", "customstyle.templates.doctor.name",
        "Audience: clinical documentation or patient-facing communication.\n"
        "Infer the type (clinical/progress note, patient letter, or referral) and format accordingly.\n"
        "- Register for clinical notes: objective, concise, clinical. For patient letters: plain,\n"
        "  clear, empathetic, jargon-free.\n"
        "- NEVER invent symptoms, findings, history, diagnoses, medications, doses, results, or\n"
        "  follow-up. Mark any gap as [confirm: ...].\n"
        "- Preserve all clinical figures, units, dates, and medication names exactly.\n"
        "- For a clinical note, organize into Subjective / Objective / Assessment / Plan ONLY where\n"
        "  the dictated content supports those sections; otherwise use clean structured prose.\n"
        "- This is a draft to be checked against the medical record before use.",
    ),
    StyleTemplate(
        "🧠", "customstyle.templates.psychotherapist.name",
        "Audience: session/progress notes or a treatment summary.\n"
        "- Register: professional, clinical, and humane. Handle distressing content neutrally and\n"
        "  without dramatizing.\n"
        "- NEVER add clinical observations, interpretations, risk assessments, or diagnoses beyond\n"
        "  what was dictated. Mark gaps as [confirm: ...].\n"
        "- Preserve the client's own words where the speaker quotes them.\n"
        "- Do not introduce identifying details that were not dictated.\n"
        "- Structure a progress note as presenting concerns / themes discussed / interventions /\n"
        "  plan, but only with sections the content actually supports.",
    ),
    StyleTemplate(
        "💼", "customstyle.templates.financial_advisor.name",
        "Audience: client meeting notes, suitability/record documentation, or a follow-up letter.\n"
        "- Register: professional, precise, compliance-aware.\n"
        "- NEVER invent or alter figures, percentages, product names, recommendations, risk\n"
        "  disclosures, or suitability rationale. Mark any uncertain number as [confirm figure].\n"
        "- Do not add advice, projections, guarantees, or promissory language that was not dictated.\n"
        "- Keep records factual and defensible; preserve all amounts, dates, and account references.\n"
        "- Structure notes as: discussion summary / decisions / agreed next steps (with owner and\n"
        "  date where stated).",
    ),
    StyleTemplate(
        "🧲", "customstyle.templates.recruiter.name",
        "Audience: candidate notes, interview feedback, outreach email, or a job description.\n"
        "Infer the type and format accordingly.\n"
        "- Register: warm-professional for candidate-facing comms; crisp and structured for internal notes.\n"
        "- Do NOT invent qualifications, scores, or feedback; keep all evaluative statements tied to\n"
        "  what was actually said.\n"
        "- Do not introduce commentary on protected characteristics or any biased framing.\n"
        "- For interview feedback, structure as: summary / strengths / concerns / recommendation —\n"
        "  using only what was dictated.",
    ),
    StyleTemplate(
        "📈", "customstyle.templates.salesperson.name",
        "Audience: call notes, a follow-up email, a CRM entry, or a short proposal snippet.\n"
        "Infer the type and format accordingly.\n"
        "- Register: professional and persuasive but never pushy for external messages; terse and\n"
        "  scannable for CRM/internal notes.\n"
        "- Do NOT invent commitments, prices, terms, features, or promises. Preserve any numbers,\n"
        "  dates, and agreed next steps exactly.\n"
        "- For call notes, structure as: summary / key points / next steps (owner + date where stated).\n"
        "- For a follow-up email, keep it concise with one clear call to action.",
    ),
    StyleTemplate(
        "🎧", "customstyle.templates.support.name",
        "Audience: a customer-facing ticket reply, an internal ticket note, or a knowledge-base snippet.\n"
        "Infer the type and format accordingly.\n"
        "- Register: clear, friendly, solution-oriented. Customer-facing text avoids internal jargon;\n"
        "  internal notes stay precise and technical.\n"
        "- Do NOT invent solutions, steps, policies, timelines, or commitments (refunds, ETAs) that\n"
        "  were not stated. Mark uncertain policy as [confirm policy].\n"
        "- Keep any troubleshooting steps accurate and in order.\n"
        "- For a customer reply, structure as: acknowledgment / clear steps or answer / next action.",
    ),
    StyleTemplate(
        "🛡️", "customstyle.templates.insurance_agent.name",
        "Audience: claim notes, a client-facing explanation of policy/coverage, or an internal report.\n"
        "Infer the type and format accordingly.\n"
        "- Register: professional, precise, compliance-aware. Plain language when explaining terms to\n"
        "  a client; exact and structured for internal claim records.\n"
        "- NEVER invent coverage details, claim facts, amounts, dates, policy/claim numbers, or\n"
        "  determinations. Mark any gap as [confirm: ...].\n"
        "- Keep records factual and defensible; preserve every figure, date, and reference verbatim.",
    ),
    StyleTemplate(
        "🏢", "customstyle.templates.professional.name",
        "Audience: general professional business writing — email, memo, message, or summary.\n"
        "Infer the most likely type from the content and format accordingly.\n"
        "- Register: clear, concise, professional.\n"
        "- Organize into a logical structure; lead with the main point; keep paragraphs tight.\n"
        "- Do not over-formalize a short message.",
    ),
    StyleTemplate(
        "💻", "customstyle.templates.programmer.name",
        "Audience: technical writing — PR description, commit message, bug report, technical note,\n"
        "design note, or a ticket/Slack update. Infer the type and format accordingly.\n"
        "- Register: terse, precise, technical. No filler, no marketing tone.\n"
        "- Use correct technical terminology freely; do not oversimplify or \"translate\" technical terms.\n"
        "- Preserve exact identifiers verbatim: function names, file paths, commands, version numbers,\n"
        "  and error strings. Do NOT invent APIs, versions, repro steps, or error messages — mark [confirm].\n"
        "- Use Markdown where it helps: bullet lists for changes, `inline code` for identifiers,\n"
        "  headings for longer docs.\n"
        "- Format conventions:\n"
        "  - Bug report → Steps to reproduce / Expected / Actual / Environment (only sections given).\n"
        "  - PR description → Summary / Changes / Notes.\n"
        "  - Commit message → concise imperative subject line, optional body.",
    ),
]
