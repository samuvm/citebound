"""R9 · Ollama corre en el host, Postgres en contenedor y por digest.

El error que esta regla existe para impedir no da la cara: meter Ollama en `compose.yaml`
funciona, arranca y responde. Solo que Docker en macOS no pasa la GPU, y todo se vuelve
entre 5 y 20 veces mas lento — el presupuesto de `G-TTFT` se cae y nadie entiende por que,
porque no hay error, hay lentitud.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

COMPOSE = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "compose.yaml").read_text(encoding="utf-8")
)
SERVICIOS = COMPOSE["services"]


def test_there_is_no_ollama_service() -> None:
    """The whole of R9 in one assertion."""
    for nombre, servicio in SERVICIOS.items():
        assert "ollama" not in nombre.lower()
        assert "ollama" not in str(servicio.get("image", "")).lower()


@pytest.mark.parametrize("nombre", list(SERVICIOS))
def test_every_image_is_pinned_by_digest_and_never_by_tag(nombre: str) -> None:
    """A tag is mutable and a digest is not (constitución §7.2). `pgvector:0.8.6` can
    point at different bytes next month, and then two people measure recall over
    different builds while both believe they used the same one."""
    imagen = SERVICIOS[nombre]["image"]
    assert "@sha256:" in imagen, f"{nombre} usa un tag: {imagen}"


def test_postgres_is_the_image_the_ddl_was_verified_against() -> None:
    assert SERVICIOS["postgres"]["image"].endswith(
        "691673308c99d2161ba298736f3147f1f22d79de2fb7ec93ae9b4afcab870b62"
    )


def test_the_port_is_configurable_because_the_machine_is_shared() -> None:
    """D-03: five projects on one laptop. On 2026-08-10 both 5432 and 5433 were already
    taken by other work, so the port is an environment variable and not an edit."""
    (puerto,) = SERVICIOS["postgres"]["ports"]
    assert puerto.startswith("${CITEBOUND_PG_PORT:-")


def test_the_data_volume_is_mounted_where_postgres_18_expects_it() -> None:
    """`/var/lib/postgresql`, not `.../data`. PG18 moved to major-version subdirectories
    so that `pg_upgrade --link` does not cross a mount boundary; every tutorial written
    before 2026 says `.../data`, and with it the container starts and exits 1."""
    volumenes = SERVICIOS["postgres"]["volumes"]
    assert any(v.endswith(":/var/lib/postgresql") for v in volumenes), volumenes
    assert not any(v.endswith(":/var/lib/postgresql/data") for v in volumenes)


def test_postgres_declares_a_healthcheck_so_that_up_can_wait() -> None:
    """`make up` uses `--wait`. Without a healthcheck it returns while the database is
    still starting, and the first command after it fails for no visible reason."""
    assert "healthcheck" in SERVICIOS["postgres"]


def test_the_route_to_the_host_is_declared_even_though_nothing_uses_it_yet() -> None:
    """`host.docker.internal` is already wired so that the day something inside the
    container needs Ollama, nobody is tempted to put Ollama inside the container."""
    assert "host.docker.internal:host-gateway" in SERVICIOS["postgres"]["extra_hosts"]
