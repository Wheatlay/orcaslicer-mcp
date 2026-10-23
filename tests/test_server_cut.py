import json

import httpx
import respx

import orcaslicer_mcp.server as srv


def _env(m):
    m.setenv("ORCA_API_TOKEN", "tok"); m.setenv("ORCA_API_URL", "http://x:13130")


@respx.mock
async def test_cut_object_composes_body(monkeypatch):
    _env(monkeypatch)
    route = respx.post("http://x:13130/api/v1/objects/7/cut").mock(
        return_value=httpx.Response(200, json={"cut": True, "dowels": 1, "warnings": [],
                                               "objects": [{"id": 11}, {"id": 12}, {"id": 13}]}))
    dowel = {"pos": [110, 110, 10], "radius": 2.5, "height": 8}
    out = await srv.cut_object(7, point=[110, 110, 10], normal=[0, 0, 1], connectors=[dowel])
    assert out["cut"] is True and [o["id"] for o in out["objects"]] == [11, 12, 13]
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"plane": {"point": [110, 110, 10], "normal": [0, 0, 1]},
                    "place_on_cut": True, "instance": 0, "connectors": [dowel]}


@respx.mock
async def test_cut_object_without_connectors_omits_them(monkeypatch):
    _env(monkeypatch)
    route = respx.post("http://x:13130/api/v1/objects/7/cut").mock(
        return_value=httpx.Response(200, json={"cut": True, "objects": [], "dowels": 0, "warnings": []}))
    await srv.cut_object(7, point=[0, 0, 5], normal=[1, 0, 0], place_on_cut=False)
    sent = json.loads(route.calls.last.request.content)
    assert "connectors" not in sent and sent["place_on_cut"] is False


@respx.mock
async def test_cut_object_plane_misses_keeps_message(monkeypatch):
    _env(monkeypatch)
    respx.post("http://x:13130/api/v1/objects/7/cut").mock(
        return_value=httpx.Response(422, json={"error": "plane_misses_object"}))
    out = await srv.cut_object(7, point=[0, 0, 999], normal=[0, 0, 1])
    assert "plane_misses_object" in json.dumps(out)


@respx.mock
async def test_cut_object_unknown_object_is_not_reported_as_missing_route(monkeypatch):
    _env(monkeypatch)
    respx.post("http://x:13130/api/v1/objects/99/cut").mock(
        return_value=httpx.Response(404, json={"error": "unknown_object"}))
    out = await srv.cut_object(99, point=[0, 0, 5], normal=[0, 0, 1])
    assert "not available on this OrcaSlicer build" not in out["error"]


@respx.mock
async def test_cut_object_on_old_build_says_so(monkeypatch):
    _env(monkeypatch)
    respx.post("http://x:13130/api/v1/objects/7/cut").mock(
        return_value=httpx.Response(404, json={"error": "not_found"}))
    out = await srv.cut_object(7, point=[0, 0, 5], normal=[0, 0, 1])
    assert "not available on this OrcaSlicer build" in out["error"]
