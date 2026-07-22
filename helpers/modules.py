
import re, os, importlib, importlib.util, inspect, sys
from types import ModuleType
from typing import Any, Type, TypeVar
from helpers.files import get_abs_path
from fnmatch import fnmatch


T = TypeVar("T")  # Define a generic type variable


def import_module(file_path: str) -> ModuleType:
    # Handle file paths with periods in the name using importlib.util
    abs_path = get_abs_path(file_path)
    module_name = os.path.basename(abs_path).replace(".py", "")

    # Create the module spec and load the module
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {abs_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_classes_from_folder(
    folder: str, name_pattern: str, base_class: Type[T], one_per_file: bool = True
) -> list[Type[T]]:
    classes = []
    abs_folder = get_abs_path(folder)

    # Get all .py files in the folder that match the pattern, sorted alphabetically
    py_files = sorted(
        [
            file_name
            for file_name in os.listdir(abs_folder)
            if fnmatch(file_name, name_pattern) and file_name.endswith(".py")
        ]
    )

    # Iterate through the sorted list of files
    for file_name in py_files:
        file_path = os.path.join(abs_folder, file_name)
        # Use the new import_module function
        module = import_module(file_path)

        # Get all classes in the module
        class_list = inspect.getmembers(module, inspect.isclass)

        # Filter for classes that are subclasses of the given base_class
        # iterate backwards to skip imported superclasses
        for cls in reversed(class_list):
            if cls[1] is not base_class and issubclass(cls[1], base_class):
                classes.append(cls[1])
                if one_per_file:
                    break

    return classes


def load_classes_from_file(
    file: str, base_class: type[T], one_per_file: bool = True
) -> list[type[T]]:
    classes = []
    # Use the new import_module function
    module = import_module(file)

    # Get all classes in the module
    class_list = inspect.getmembers(module, inspect.isclass)

    def _matches(cls) -> bool:
        return cls is not base_class and issubclass(cls, base_class)

    # Prefer classes actually DEFINED in this file over ones it imported.
    #
    # This used to walk the member list backwards and take the first match,
    # with the comment "iterate backwards to skip imported superclasses". That
    # works only by accident: inspect.getmembers sorts alphabetically, so
    # reversing it picks whichever name sorts LAST, and a subclass only wins if
    # its name happens to sort after its parent's.
    #
    # ScoopyChat beat MessageAsync and ScoopyChatPoll beat Poll, so the trick
    # looked sound. ScoopyTranscribe lost to Transcribe, because S sorts before
    # T. The route then dispatched to Agent Zero's stock handler, which requires
    # CSRF, so every server-to-server voice transcription answered 403 with
    # "CSRF token missing or invalid" no matter what the subclass declared.
    # Verified against production 2026-07-22 and reproduced from the names
    # alone. Renaming the class would have hidden it until the next collision.
    #
    # `__module__` is the honest test of "defined here", and it is exactly what
    # the original comment was reaching for.
    own = [c for _, c in class_list if _matches(c) and c.__module__ == module.__name__]

    # Falls back to the old behaviour when a file genuinely only re-exports a
    # handler, so nothing that relied on that keeps working by luck alone.
    if not own:
        own = [c for _, c in reversed(class_list) if _matches(c)]

    for cls in own:
        classes.append(cls)
        if one_per_file:
            break

    return classes


def purge_namespace(namespace: str):
    to_delete = [
        name
        for name in sys.modules
        if name == namespace or name.startswith(namespace + ".")
    ]

    # delete deepest first just to be tidy
    to_delete.sort(key=lambda n: n.count("."), reverse=True)

    for name in to_delete:
        del sys.modules[name]

    importlib.invalidate_caches()
    return to_delete