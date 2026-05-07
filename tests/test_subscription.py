import pytest
from core.heuristics import estimate_subscription_residential, _compute_surface_base
from tests.data.scenarios import SCENARIOS, SCENARIOS_PARAMETRIQUES


class TestSurfaceBase:
    def test_minimum(self):
        assert _compute_surface_base(25) == 6
        assert _compute_surface_base(30) == 6

    def test_progressif(self):
        assert _compute_surface_base(50) == 7
        assert _compute_surface_base(60) == 8
        assert _compute_surface_base(75) == 9
        assert _compute_surface_base(90) == 10
        assert _compute_surface_base(105) == 11

    def test_plafond(self):
        assert _compute_surface_base(120) == 12
        assert _compute_surface_base(200) == 12
        assert _compute_surface_base(500) == 12


class TestScenarioResidentiels:
    def test_tous_les_scenarios(self):
        for nom, scenario in SCENARIOS.items():
            params = {k: v for k, v in scenario.items() if k != "attendu"}
            result = estimate_subscription_residential(**params)
            attendu = scenario["attendu"]
            for key, val in attendu.items():
                assert result[key] == val, (
                    f"[{nom}] {key}: attendu {val}, obtenu {result[key]}"
                )


@pytest.mark.parametrize(
    "surface,chambres,pac,ve,atelier,ve_type,pac_type,plaque,exp_sub,exp_phase",
    SCENARIOS_PARAMETRIQUES,
)
def test_scenarios_parametres(
    surface, chambres, pac, ve, atelier, ve_type, pac_type, plaque, exp_sub, exp_phase,
):
    result = estimate_subscription_residential(
        surface, chambres,
        has_pac=pac, has_ve=ve, has_atelier=atelier,
        ve_type=ve_type, pac_type=pac_type,
        presence_plaque=plaque,
    )
    assert result["subscription"] == exp_sub
    assert result["phase"] == exp_phase


class TestHeatingChauffage:
    def test_chauffage_principal_grande_surface(self):
        result = estimate_subscription_residential(
            surface=120, nb_chambres=4,
            chauffage_type="electrique", has_pac=False,
        )
        assert "chauffage électrique principal" in result["justification"]

    def test_chauffage_moyenne_surface(self):
        result = estimate_subscription_residential(
            surface=80, nb_chambres=3,
            chauffage_type="electrique", has_pac=False,
        )
        assert result["phase"] == "monophasé"
        assert result["subscription"] in ("12 kVA", "15 kVA")

    def test_pas_de_chauffage_avec_pac(self):
        result = estimate_subscription_residential(
            surface=120, nb_chambres=4,
            has_pac=True, pac_type="air_eau",
        )
        assert "chauffage" not in result["justification"].lower()
        assert "PAC" in result["justification"]


class TestEquipements:
    def test_plaque_cuisson_ajoute_bonus(self):
        sans = estimate_subscription_residential(50, 2, presence_plaque=False)
        avec = estimate_subscription_residential(50, 2, presence_plaque=True)
        assert sans["subscription"] != avec["subscription"]

    def test_ve_lent_modifier_zero(self):
        result = estimate_subscription_residential(
            80, 3, has_ve=True, ve_type="lent",
        )
        assert result["phase"] == "monophasé"

    def test_ve_standard_modifier_deux(self):
        result = estimate_subscription_residential(
            80, 3, has_ve=True, ve_type="standard",
        )
        assert result["phase"] == "monophasé"

    def test_atelier_modifier_selon_surface(self):
        petit = estimate_subscription_residential(50, 2, has_atelier=True)
        grand = estimate_subscription_residential(160, 3, has_atelier=True)
        assert petit["phase"] == "monophasé"
        assert grand["phase"] == "triphasé"
