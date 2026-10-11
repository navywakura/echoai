"""Layout boundary for the flattened public source distribution.

These paths replace the private checkout's parent navi10_* modules. They do
not certify equivalence with historical audited source hashes. See
docs/PUBLICATION-PORTABILITY.md; algorithms and experiment gates are unchanged.
"""

CORE_FILES = tuple(f'core/{name}.py' for name in
                   ('__init__', 'qn', 'cam', 'wsp', 'stdp', 'spoke', 'dag'))
