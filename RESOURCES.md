# Python and FastAPI Resources

## Knowledge

- [Python: `contextlib` and `asynccontextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager)
  Official definition of the decorator used by the API lifespan function. Use for: `yield`, setup, cleanup, and asynchronous context managers.
- [Python: `typing`](https://docs.python.org/3/library/typing.html)
  Official reference for type annotations such as `Literal`, return types, and `AsyncIterator`. Use for: understanding the syntax after `:` and `->`.
- [FastAPI: Python types](https://fastapi.tiangolo.com/python-types/)
  Official explanation of how FastAPI reads standard Python annotations and `Annotated` metadata. Use for: endpoint parameters and validation.
- [FastAPI: lifespan events](https://fastapi.tiangolo.com/advanced/events/)
  Official startup/shutdown pattern used by this project. Use for: the `lifespan` function and shared runtime state.
- [Python: `argparse`](https://docs.python.org/3/library/argparse.html)
  Official command-line parser reference. Use for: `ArgumentParser`, option definitions, namespaces, and parser errors.
- [Python: data classes](https://docs.python.org/3/library/dataclasses.html)
  Official behavior of `@dataclass`. Use for: generated constructors, frozen value objects, and `__post_init__`.
- [Python: `unittest.mock`](https://docs.python.org/3/library/unittest.mock.html)
  Official mocking and patching reference. Use for: understanding fake adapters and temporary substitutions in tests.
- [ONNX Runtime: Python API](https://onnxruntime.ai/docs/api/python/api_summary.html)
  Official `InferenceSession` API. Use for: model sessions, providers, model inputs, and `session.run`.
- [Docker: optimize build cache](https://docs.docker.com/build/cache/optimize/)
  Official cache-layer and cache-mount guidance. Use for: understanding Dockerfile ordering and pip download reuse.

## Wisdom (Communities)

- [FastAPI GitHub Discussions](https://github.com/fastapi/fastapi/discussions)
  Maintainer and practitioner discussions. Use later for: checking real-world design questions after the core syntax is understood.
