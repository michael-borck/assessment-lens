"""Capability manifest — family-consistent identity for the lens's HTTP face.

A lens is a *consumer*, not a routable analyser: it takes a rubric + a folder of
submissions, not a single file by extension. So ``auto_routable`` is false and
there are no ``extensions`` — but it still exposes the same ``/manifest`` +
``/health`` contract so a desktop shell (or any UI) can discover and talk to it.
"""

from lens_contract import make_manifest

MANIFEST = make_manifest(
    name="assessment-lens",
    accepts=["submissions"],
    produces="AssessmentResult",
    extensions=[],
    auto_routable=False,  # invoked deliberately with a rubric, never routed to by file type
    role="lens",
)
