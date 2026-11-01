import json
from django.test import TestCase, AsyncRequestFactory
from portal.views import triage_api, clinical_rule_fallback, RED_FLAG_SYMPTOMS

class TriageApiTests(TestCase):
    def setUp(self):
        self.rf = AsyncRequestFactory()

    async def test_red_flag_chest_pain(self):
        """Red flag symptoms must return EMERGENCY immediately without API call."""
        request = self.rf.post(
            '/api/triage/',
            data=json.dumps({'symptom': 'I am experiencing severe chest pain and pressure'}),
            content_type='application/json'
        )
        response = await triage_api(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['urgency'], 'EMERGENCY')
        self.assertEqual(data['badge_color'], 'red')
        self.assertTrue(data['highlight_clinics'])

    async def test_empty_symptom(self):
        """Empty symptom string returns 400."""
        request = self.rf.post(
            '/api/triage/',
            data=json.dumps({'symptom': ''}),
            content_type='application/json'
        )
        response = await triage_api(request)
        self.assertEqual(response.status_code, 400)

    async def test_method_not_allowed(self):
        """GET request returns 405."""
        request = self.rf.get('/api/triage/')
        response = await triage_api(request)
        self.assertEqual(response.status_code, 405)

    def test_clinical_rule_fallback_minor(self):
        """Minor keywords return SELF_CARE."""
        result = clinical_rule_fallback('mild burn on index finger')
        self.assertEqual(result['urgency'], 'SELF_CARE')
        self.assertEqual(result['badge_color'], 'green')
        self.assertFalse(result['highlight_clinics'])
        self.assertIn('first-aid', result['guidance'].lower())

    def test_clinical_rule_fallback_moderate(self):
        """Moderate keywords return OPD."""
        result = clinical_rule_fallback('high fever and severe cough')
        self.assertEqual(result['urgency'], 'OPD')
        self.assertEqual(result['badge_color'], 'yellow')
        self.assertTrue(result['highlight_clinics'])
        self.assertIn('opd', result['guidance'].lower())

    def test_clinical_rule_fallback_high(self):
        """High severity keywords return EMERGENCY."""
        result = clinical_rule_fallback('difficulty in breath and sudden faint')
        self.assertEqual(result['urgency'], 'EMERGENCY')
        self.assertEqual(result['badge_color'], 'red')
        self.assertTrue(result['highlight_clinics'])
