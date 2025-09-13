from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from google_adk_extras.wrappers.artifact_list_wrapper import ArtifactListWrapperMiddleware


def make_app(names):
    async def list_artifacts(request):
        return JSONResponse(names)

    return Starlette(routes=[Route("/apps/app/users/u/sessions/s1/artifacts", list_artifacts)])


def test_artifact_list_filters_sort_limit():
    names = ["a.txt", "b.txt", "alpha.json", "beta.csv", "gamma.txt"]
    app = make_app(names)
    app.add_middleware(ArtifactListWrapperMiddleware)
    client = TestClient(app)
    r = client.get(
        "/apps/app/users/u/sessions/s1/artifacts",
        params={
            "prefix": "a",
            "contains": ".t",
            "sort": "name_desc",
            "limit": "1",
        },
    )
    assert r.status_code == 200
    body = r.json()
    # names starting with 'a' and containing '.t' => ['a.txt'] then desc -> same, limit 1
    assert body == ["a.txt"]

