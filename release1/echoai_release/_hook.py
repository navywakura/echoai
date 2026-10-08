"""Loaded from echoai_release.pth at interpreter start (release venv only).

1. It waits until `echoai` is imported and then activates the release identity.
   Processes the agent spawns itself (fresh-process resume) get it too, because
   they start from the same interpreter and site-packages.
2. `python -m echoai.<module>` needs a code object, which compiled modules do not
   have. For that one target module only, it runs the module's own
   `if __name__ == "__main__":` block (shipped as text in the build manifest: CLI
   glue only) on top of the compiled module. Nothing else is touched.
"""
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys


class _ActivateAfterEchoai(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name != "echoai":
            return None
        if self in sys.meta_path:
            sys.meta_path.remove(self)
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None or spec.loader is None:
            return spec
        original = spec.loader.exec_module

        def exec_module(module, _original=original):
            _original(module)
            from echoai_release import identity
            identity.activate()
        try:
            spec.loader.exec_module = exec_module
        except (AttributeError, TypeError):
            pass
        return spec


class _MainShim(importlib.abc.Loader):
    """Serves `python -m <target>` for a compiled echoai module, once.

    runpy asks importlib.util.find_spec(target) (or target.__main__ for a package).
    That single lookup is answered with this loader; every ordinary import of the same
    module still gets the compiled one.
    """

    def __init__(self, target):
        self.target, self.used, self.block = target, False, None

    def spec_for(self, name):
        if self.used or name not in (self.target, self.target + ".__main__"):
            return None
        from echoai_release import identity
        block = identity.manifest().get("main_blocks", {}).get(name)
        if block is None:
            return None
        self.used, self.block = True, block
        return importlib.util.spec_from_loader(name, self, origin="echoai-release-main:" + name)

    def create_module(self, spec):
        return None

    def get_code(self, fullname):
        prefix = ("import importlib as _echoai_il\n"
                  "_echoai_m = _echoai_il.import_module(%r)\n"
                  "globals().update({_k: _v for _k, _v in vars(_echoai_m).items()\n"
                  "                  if not (_k.startswith('__') and _k.endswith('__'))})\n" % fullname)
        return compile(prefix + self.block + "\n", "<echoai-main:%s>" % fullname, "exec")

    def exec_module(self, module):
        exec(self.get_code(module.__name__), module.__dict__)


def install():
    if "echoai" not in sys.modules and not any(isinstance(f, _ActivateAfterEchoai) for f in sys.meta_path):
        sys.meta_path.insert(0, _ActivateAfterEchoai())
    argv = getattr(sys, "orig_argv", [])
    if "-m" in argv:
        i = argv.index("-m")
        if i + 1 < len(argv) and argv[i + 1].startswith("echoai.") \
                and not getattr(importlib.util.find_spec, "_echoai_shim", False):
            shim, original = _MainShim(argv[i + 1]), importlib.util.find_spec

            def find_spec(name, package=None):
                spec = shim.spec_for(name) if package is None else None
                return spec if spec is not None else original(name, package)
            find_spec._echoai_shim = True
            importlib.util.find_spec = find_spec


install()
