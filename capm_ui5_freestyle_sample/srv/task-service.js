/*
============================================================
SERVICE IMPLEMENTATION — the "complete" action + a few guardrails
============================================================
Use this when: implementing bound/unbound actions and simple
validation handlers. Kept intentionally small — most of what a CAP
service needs (plain CRUD) is FREE via `@sap/cds/common`'s
generic handlers; you only write code for what's genuinely custom.
============================================================
*/
const cds = require('@sap/cds');

module.exports = class TaskService extends cds.ApplicationService {
  init() {
    const { Tasks } = this.entities;

    // Bound action: Tasks(<ID>)/TaskService.complete()
    this.on('complete', Tasks, async (req) => {
      const task = await SELECT.one.from(req.subject);
      if (!task) return req.error(404, 'Task not found');
      if (task.status === 'Done') {
        return req.error(400, `Task '${task.title}' is already Done`);
      }
      await UPDATE(req.subject).with({ status: 'Done' });
      return SELECT.one.from(req.subject);
    });

    // Unbound action: TaskService.resetDemoData()
    this.on('resetDemoData', async () => {
      await UPDATE(Tasks).set({ status: 'Open' }).where({ status: 'Done' });
      return 'Demo data reset — all Done tasks moved back to Open';
    });

    // Simple server-side guardrail beyond the @assert.range enum
    // check already on the CDS model: due dates can't be in the past
    // for NEWLY created tasks (existing overdue tasks are fine to
    // keep as-is, hence this only fires on CREATE, not UPDATE).
    this.before('CREATE', Tasks, (req) => {
      const { dueDate } = req.data;
      if (dueDate && dueDate < new Date().toISOString().slice(0, 10)) {
        req.error(400, 'Due date cannot be in the past', 'dueDate');
      }
    });

    return super.init();
  }
};

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why does `complete` re-SELECT the task after the UPDATE instead
   of just returning `{ ...task, status: 'Done' }`?
A: `req.subject` already carries the exact key predicate for
   whichever Task the action was called on — re-reading confirms
   the ACTUAL persisted row (picking up any other server-side
   defaults/computed fields that might differ from a hand-built
   object) and is what the OData action's `returns Tasks` response
   type expects: a full, current entity representation, not just
   the fields this handler happens to know about.

Q: This action is BOUND (`entity Tasks as projection ... actions {
   action complete() ... }`) while `resetDemoData` is UNBOUND — how
   does that change the client-side call in TaskDetail.controller.js?
A: A bound action's OData path includes the instance key:
   `POST /Tasks(ID=...)/TaskService.complete`, and in UI5 you invoke
   it via the binding CONTEXT: `oContext.getBinding().execute()` (v4
   ODataListBinding/ODataContextBinding-style) or, as this template
   does for simplicity, a manual `oModel.bindContext(...)`. An
   unbound action has no instance context at all — just
   `POST /TaskService.resetDemoData`, called via
   `oModel.bindContext("/resetDemoData(...)")` with no leading
   entity key.
------------------------------------------------------------
*/
