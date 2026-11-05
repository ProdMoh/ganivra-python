"""Explicit REST resources. Payloads and filters follow the Ganivra API schema.

Each helper's docstring names the HTTP method and path it calls.
"""
from typing import Any, Mapping
from urllib.parse import quote


class Resource:
    def __init__(self, client):
        self._client = client


class Events(Resource):
    def correct(self, event_id: str, *, payload: Mapping[str, Any], params=None) -> Any:
        """POST /v1/events/{event_id}/corrections. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/events/{quote(event_id, safe="")}/corrections', payload=payload, params=params)

    def history(self, event_id: str, *, params=None) -> Any:
        """GET /v1/events/{event_id}/history. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/events/{quote(event_id, safe="")}/history', params=params)

    def create(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/events. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/events', params=params, payload=payload)

    def create_batch(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/events. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/events', params=params, payload=payload)


class Revenue(Resource):
    def create(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/revenue. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/revenue', params=params, payload=payload)

    def import_entries(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/revenue/import. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/revenue/import', params=params, payload=payload)


class PricingPlans(Resource):
    def create(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/pricing-plans. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/pricing-plans', params=params, payload=payload)

    def update_dates(self, plan_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/pricing-plans/{plan_id}/dates. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/pricing-plans/{quote(plan_id, safe="")}/dates', params=params, payload=payload)


class CustomerPlans(Resource):
    def assign(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/customer-plans. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/customer-plans', params=params, payload=payload)

    def update_dates(self, assignment_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/customer-plans/{assignment_id}/dates. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/customer-plans/{quote(assignment_id, safe="")}/dates', params=params, payload=payload)


class Economics(Resource):
    def get(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/economics. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/economics', params=params)

    def create_contract_rate(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/contract-rates. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/contract-rates', params=params, payload=payload)

    def reconcile(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/reconciliations. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/reconciliations', params=params, payload=payload)

    def reprice(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/reprice. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/reprice', params=params, payload=payload)

    def transaction(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/transactions. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/transactions', params=params, payload=payload)

    def create_model_policy(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/model-policies. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/model-policies', params=params, payload=payload)

    def gpu_pools(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/economics/gpu-pools. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/economics/gpu-pools', params=params)

    def gpu_tenants(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/economics/gpu-tenants. Pass days in params for the period."""
        return self._client.request('GET', f'/v1/economics/gpu-tenants', params=params)

    def gpu_move_analysis(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/economics/gpu-move-analysis. Pass pool_id, or hourly_rate_usd and tokens_per_gpu_second, in params."""
        return self._client.request('GET', f'/v1/economics/gpu-move-analysis', params=params)

    def create_gpu_pool(self, *, payload: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/gpu-pools. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/gpu-pools', params=params, payload=payload)

    def end_gpu_pool(self, pool_id: str, *, payload: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/gpu-pools/{pool_id}/end. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/economics/gpu-pools/{pool_id}/end', params=params, payload=payload)

    def delete_gpu_pool(self, pool_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """DELETE /v1/economics/gpu-pools/{pool_id}. Pass REST fields in payload/params."""
        return self._client.request('DELETE', f'/v1/economics/gpu-pools/{pool_id}', params=params)


class Delivery(Resource):
    def create(self, *, payload: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/delivery-costs/events. Pass REST fields in payload/params."""
        return self.create_batch(payload={'events': [payload]}, params=params)

    def create_batch(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/delivery-costs/events. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/delivery-costs/events', params=params, payload=payload)

    def import_events(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/delivery-costs/import. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/delivery-costs/import', params=params, payload=payload)

    def report(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/delivery-costs. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/delivery-costs', params=params)

    def set_bill_policy(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/delivery-costs/bill-policy. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/delivery-costs/bill-policy', params=params, payload=payload)

    def create_snapshot(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/delivery-costs/snapshots. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/delivery-costs/snapshots', params=params, payload=payload)

    def get_snapshot(self, snapshot_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/delivery-costs/snapshots/{snapshot_id}. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/delivery-costs/snapshots/{quote(snapshot_id, safe="")}', params=params)

    def investigate(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/delivery-costs/investigation. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/delivery-costs/investigation', params=params)

    def evidence(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/delivery-costs/evidence. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/delivery-costs/evidence', params=params)


class Reports(Resource):
    def costs(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/reports/costs. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/reports/costs', params=params)

    def export(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/reports/costs/export. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/reports/costs/export', params=params, raw=True)

    def allocation_rules(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/reports/allocation-rules. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/reports/allocation-rules', params=params)

    def create_allocation_rule(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/reports/allocation-rules. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/reports/allocation-rules', params=params, payload=payload)

    def retire_allocation_rule(self, rule_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/reports/allocation-rules/{rule_id}/retire. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/reports/allocation-rules/{quote(rule_id, safe="")}/retire', params=params, payload=payload)

    def reconcile(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/reports/reconciliations. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/reports/reconciliations', params=params, payload=payload)

    def emissions(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/reports/emissions. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/reports/emissions', params=params)

    def export_emissions(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/reports/emissions/export. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/reports/emissions/export', params=params, raw=True)

    def recalculate_emissions(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/reports/emissions/recalculate. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/reports/emissions/recalculate', params=params, payload=payload)


class Bills(Resource):
    def list(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/bills. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/bills', params=params)

    def preview(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/bills/preview. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/bills/preview', params=params, payload=payload)

    def import_rows(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/bills/import. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/bills/import', params=params, payload=payload)

    def void(self, line_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/bills/{line_id}/void. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/bills/{quote(line_id, safe="")}/void', params=params, payload=payload)


class Budgets(Resource):
    def list(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/budgets. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/budgets', params=params)

    def create(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/budgets. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/budgets', params=params, payload=payload)

    def evaluate(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/budgets/evaluate. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/budgets/evaluate', params=params, payload=payload)

    def review(self, budget_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/budgets/{budget_id}/reviews. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/budgets/{quote(budget_id, safe="")}/reviews', params=params, payload=payload)

    def set_owner(self, budget_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/budgets/{budget_id}/owner. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/budgets/{quote(budget_id, safe="")}/owner', params=params, payload=payload)

    def archive(self, budget_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/budgets/{budget_id}/archive. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/budgets/{quote(budget_id, safe="")}/archive', params=params, payload=payload)


class Workspaces(Resource):
    def list(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/partners/clients. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/partners/clients', params=params)

    def create(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/partners/clients. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/partners/clients', params=params, payload=payload)

    def get(self, workspace_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/partners/clients/{workspace_id}. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/partners/clients/{quote(workspace_id, safe="")}', params=params)

    def rename(self, workspace_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/partners/clients/{workspace_id}/rename. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/partners/clients/{quote(workspace_id, safe="")}/rename', params=params, payload=payload)

    def rotate_key(self, workspace_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/partners/clients/{workspace_id}/api-key/rotate. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/partners/clients/{quote(workspace_id, safe="")}/api-key/rotate', params=params, payload=payload)

    def access(self, workspace_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/partners/clients/{workspace_id}/access. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/partners/clients/{quote(workspace_id, safe="")}/access', params=params)

    def grant_access(self, workspace_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/partners/clients/{workspace_id}/access. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/partners/clients/{quote(workspace_id, safe="")}/access', params=params, payload=payload)

    def revoke_access(self, workspace_id: str, user_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/partners/clients/{workspace_id}/access/{user_id}/revoke. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/partners/clients/{quote(workspace_id, safe="")}/access/{quote(user_id, safe="")}/revoke', params=params, payload=payload)


class Audit(Resource):
    def list(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/audit. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/audit', params=params)

    def export(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/audit/export. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/audit/export', params=params, raw=True)


class Account(Resource):
    def consumption(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/account/consumption. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/account/consumption', params=params)

    def bootstrap(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/account/bootstrap. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/account/bootstrap', params=params, payload=payload)

    def rotate_key(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/account/api-key/rotate. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/account/api-key/rotate', params=params, payload=payload)

    def profile(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/account/profile. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/account/profile', params=params)

    def save_profile(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """PUT /v1/account/profile. Pass REST fields in payload/params."""
        return self._client.request('PUT', f'/v1/account/profile', params=params, payload=payload)


class Executions(Resource):
    def list(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/executions. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/executions', params=params)

    def get(self, execution_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/executions/{execution_id}. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/executions/{quote(execution_id, safe="")}', params=params)

    def dashboard(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/dashboard. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/dashboard', params=params)


class Value(Resource):
    def list(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/value. Pass REST fields in payload/params."""
        return self._client.request('GET', '/v1/value', params=params)

    def import_assessment(self, *, payload: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/value/import. Pass REST fields in payload/params."""
        return self._client.request('POST', '/v1/value/import', payload=payload, params=params)


class Transactions(Resource):
    def create(self, *, payload: Mapping[str, Any], params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/economics/transactions. Pass REST fields in payload/params."""
        return self._client.request('POST', '/v1/economics/transactions', payload=payload, params=params)


class MarginReview(Resource):
    def get(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review', params=params)

    def customers(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/customers. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/customers', params=params)

    def activate(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/activate. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/activate', params=params, payload=payload)

    def configure(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/configure. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/configure', params=params, payload=payload)

    def generate(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/generate. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/generate', params=params, payload=payload)

    def review(self, review_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/reviews/{review_id}. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/reviews/{quote(review_id, safe="")}', params=params)

    def action(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/actions. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/actions', params=params, payload=payload)

    def review_pdf(self, review_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/reviews/{review_id}/pdf. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/reviews/{quote(review_id, safe="")}/pdf', params=params, raw=True)

    def board_update(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/board-update. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/board-update', params=params)

    def board_update_pdf(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/board-update/pdf. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/board-update/pdf', params=params, raw=True)


class SpendClose(Resource):
    def get(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/close. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/close', params=params)

    def observed(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/close/observed. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/close/observed', params=params)

    def configure(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/close/configure. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/close/configure', params=params, payload=payload)

    def prepare(self, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/close/prepare. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/close/prepare', params=params, payload=payload)

    def pack(self, pack_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/close/packs/{pack_id}. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/close/packs/{quote(pack_id, safe="")}', params=params)

    def decide(self, pack_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/close/packs/{pack_id}/decisions. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/close/packs/{quote(pack_id, safe="")}/decisions', params=params, payload=payload)

    def transition(self, pack_id: str, *, payload: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        """POST /v1/margin-review/close/packs/{pack_id}/transition. Pass REST fields in payload/params."""
        return self._client.request('POST', f'/v1/margin-review/close/packs/{quote(pack_id, safe="")}/transition', params=params, payload=payload)

    def pack_pdf(self, pack_id: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """GET /v1/margin-review/close/packs/{pack_id}/pdf. Pass REST fields in payload/params."""
        return self._client.request('GET', f'/v1/margin-review/close/packs/{quote(pack_id, safe="")}/pdf', params=params, raw=True)
