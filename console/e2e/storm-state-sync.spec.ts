import { readFileSync } from "node:fs";
import { test, expect, type Page } from "@playwright/test";
import {
  listEmailFiles,
  signUpViaMagicLink,
  waitForNewEmailLink,
  withEmailLock,
} from "./helpers/auth";

// The storm page, as the people using it see it. It holds several views of
// "which cycle" -- the one on screen (the cycle-context panel, the map, the
// highlighted Past-cycles chip), the one the "Run a new cycle" form would run
// (the text field, the date button, the hour select), and the banner from
// whatever was last tried -- and a user expects them to agree at every step.
// They didn't (EP212026 Trudy, 15 Oct 2026): viewing 06Z with 12Z the latest,
// the form offered 00Z -- a cycle the storm already had, typed by nobody --
// and running it left a 409 banner that nothing cleared.
//
// Each test is one thing someone does on the page, with what they should see
// at each step. The clock and the storms are pinned, so every state is exact.
//
// Mocked end to end (no demo API), so CI runs this against the built Worker
// too (playwright.workerd.config.ts): a demo storm and cycle as templates.

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/storm-page.json", import.meta.url), "utf8"),
) as { storm: Record<string, unknown>; cycle: Record<string, unknown> };

type Storm = Record<string, unknown> & { storm_id: string; cycles: string[] };

function stormFixture(
  stormId: string,
  name: string,
  fixIso: string,
  cycles: string[],
  { active = true } = {},
): Storm {
  const real = fixture.storm as {
    latest_fix: Record<string, unknown>;
    history: unknown[];
  };
  const fix = { ...real.latest_fix, valid_time: fixIso };
  return {
    ...fixture.storm,
    storm_id: stormId,
    name,
    basin: stormId.slice(0, 2),
    trained_basin: stormId.startsWith("AL"),
    active,
    season: 2026,
    latest_fix: fix,
    history: [...real.history.slice(0, -1), fix],
    cycles: [...cycles],
    last_cycle: cycles.at(-1) ?? null,
  };
}

function cycleFor(storm: Storm, label: string, run?: Record<string, unknown>) {
  const c = fixture.cycle as { payload: Record<string, unknown> };
  return {
    ...fixture.cycle,
    storm_id: storm.storm_id,
    payload: { ...c.payload, cycle: label },
    ...(run ? { run } : {}),
  };
}

/** Serves `storms` (mutable: a test adds cycles mid-test, as the cron or
 * another user would) and their cycles; `failCycle` labels answer 500. */
async function serve(page: Page, storms: Storm[], failCycle: string[] = []) {
  for (const storm of storms) {
    await page.route(`**/v1/storms/${storm.storm_id}`, (r) =>
      r.request().method() === "GET"
        ? r.fulfill({ json: storm })
        : r.fallback(),
    );
    await page.route(`**/v1/storms/${storm.storm_id}/cycles/*`, (r) => {
      const label = r.request().url().split("/").pop()!.split("?")[0];
      if (failCycle.includes(label)) {
        return r.fulfill({ status: 500, json: { detail: "R2 unavailable" } });
      }
      if (!storm.cycles.includes(label)) {
        return r.fulfill({ status: 404, json: { detail: "no such cycle" } });
      }
      return r.fulfill({ json: cycleFor(storm, label) });
    });
  }
}

type RunReply = { status: number; detail: string; code?: string } | "ran";

/** Answers the run form's POSTs with `replies` in turn ("ran" stores the
 * cycle and returns it, like the API). Returns the bodies sent, and a
 * `hold()` that keeps the next answer back until `release()`. */
async function answerRuns(page: Page, storm: Storm, replies: RunReply[]) {
  const sent: Record<string, unknown>[] = [];
  let gate: Promise<void> | null = null;
  let open = () => {};
  await page.route(`**/v1/storms/${storm.storm_id}/cycles`, async (r) => {
    if (r.request().method() !== "POST") return r.fallback();
    const body = r.request().postDataJSON() as Record<string, unknown>;
    sent.push(body);
    if (gate) await gate;
    const reply = replies[Math.min(sent.length - 1, replies.length - 1)];
    if (reply === "ran") {
      const label = String(body.cycle);
      if (!storm.cycles.includes(label)) storm.cycles.push(label);
      return r.fulfill({
        json: cycleFor(storm, label, { source: "manual", overrides: [] }),
      });
    }
    return r.fulfill({
      status: reply.status,
      json: {
        detail: reply.detail,
        ...(reply.code ? { code: reply.code } : {}),
      },
    });
  });
  return {
    sent,
    hold() {
      gate = new Promise((resolve) => (open = resolve));
    },
    release() {
      gate = null;
      open();
    },
  };
}

const TRUDY_CYCLES = [
  "20261013_18Z",
  "20261014_00Z",
  "20261014_06Z",
  "20261014_12Z",
  "20261014_18Z",
  "20261015_00Z",
  "20261015_06Z",
];

/** EP212026 Trudy, latest fix 12Z on 15 Oct, opened at `nowIso`. */
async function openTrudy(
  page: Page,
  nowIso: string,
  { cycles = TRUDY_CYCLES, failCycle = [] as string[] } = {},
) {
  const storm = stormFixture(
    "EP212026",
    "Trudy",
    "2026-10-15T12:00:00Z",
    cycles,
  );
  await serve(page, [storm], failCycle);
  await page.clock.install({ time: new Date(nowIso) });
  await page.goto(`/storms/${storm.storm_id}`);
  await expect(context(page)).toBeVisible({ timeout: 15_000 });
  return storm;
}

const context = (page: Page) => page.getByTestId("cycle-context");
const input = (page: Page) => page.locator("#cycle-input");
const hour = (page: Page) => page.locator("#cycle-hour-select");
const dateButton = (page: Page) => page.getByTestId("cycle-date-trigger");
const runButton = (page: Page) =>
  page.getByRole("button", { name: /^Run cycle$|^Running…$/ });
const banner = (page: Page) => page.getByTestId("page-error");
const olderCallout = (page: Page) => page.getByText(/Viewing an older cycle/);
const chip = (page: Page, label: string) =>
  page
    .getByTestId("past-cycles")
    .getByRole("button", { name: label, exact: true });

/** The text field, the date button and the hour select all say `label`. */
async function expectForm(page: Page, label: string) {
  await expect(input(page)).toHaveValue(label);
  await expect(dateButton(page)).toHaveText(label.slice(0, 8));
  await expect(hour(page)).toHaveValue(String(Number(label.slice(9, 11))));
}

/** The panel, the chips and the older-cycle callout all agree on what's on
 * screen, and whether it's the latest. */
async function expectShowing(page: Page, label: string, latest: string) {
  await expect(context(page)).toContainText(`Showing forecast cycle ${label}`);
  await expect(chip(page, label)).toHaveAttribute("aria-current", "true");
  await expect(
    page.getByTestId("past-cycles").locator('[aria-current="true"]'),
  ).toHaveCount(1);
  if (label === latest) {
    await expect(context(page)).toContainText("the latest run");
    await expect(olderCallout(page)).toBeHidden();
  } else {
    await expect(context(page)).toContainText(
      `an older run; the latest is ${latest}`,
    );
    await expect(olderCallout(page)).toBeVisible();
  }
}

test.describe("someone reading a storm", () => {
  test("opens on the newest forecast, says it is the newest, and offers the next cycle to run", async ({
    page,
  }) => {
    // 12:50Z: the 12Z cycle is on the calendar but runs at 13:30Z.
    await openTrudy(page, "2026-10-15T12:50:00Z");

    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "EP212026 Trudy",
    );
    await expectShowing(page, "20261015_06Z", "20261015_06Z");
    await expect(page.getByTestId("pending-cycle")).toContainText(
      "The 20261015_12Z cycle hasn't run yet — it's scheduled for 13:30Z",
    );
    // The form offers the pending cycle -- not one already on screen.
    await expectForm(page, "20261015_12Z");
    await expect(page.getByTestId("cycle-exists")).toBeHidden();
    await expect(banner(page)).toBeHidden();
  });

  test("is told before clicking that running needs an account, and comes back to the storm after signing in", async ({
    page,
  }) => {
    await openTrudy(page, "2026-10-15T12:50:00Z");
    const note = page.getByTestId("sign-in-to-run");
    await expect(note).toContainText("Running a cycle needs an account");

    await runButton(page).click();
    await expect(page).toHaveURL(/\/auth\/login\?next=%2Fstorms%2FEP212026$/, {
      timeout: 15_000,
    });

    await page.getByLabel("Email").fill(`return-${Date.now()}@example.com`);
    const link = await withEmailLock(async () => {
      const before = listEmailFiles();
      await page.getByRole("button", { name: "Send" }).click();
      return waitForNewEmailLink(before);
    });
    await page.goto(link);

    await expect(page).toHaveURL(/\/storms\/EP212026$/, { timeout: 15_000 });
    await expect(context(page)).toBeVisible({ timeout: 15_000 });
    await expect(note).toBeHidden();
    await expect(runButton(page)).toBeEnabled();
  });

  test("browses an older cycle and stays on it while newer ones arrive, until they go back to the latest", async ({
    page,
  }) => {
    const storm = await openTrudy(page, "2026-10-15T12:50:00Z");

    await chip(page, "20261014_18Z").click();
    await expectShowing(page, "20261014_18Z", "20261015_06Z");
    // Looking at a past cycle doesn't change what the form would run.
    await expectForm(page, "20261015_12Z");

    // The cron runs 12Z; the page's polls pick it up.
    storm.cycles.push("20261015_12Z");
    await page.clock.fastForward("50:00"); // 13:40Z
    await expect(chip(page, "20261015_12Z")).toBeVisible();
    await expectShowing(page, "20261014_18Z", "20261015_12Z");

    await page.getByRole("button", { name: "Back to latest" }).click();
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
  });

  test("following the latest, a new cycle replaces the old one on its own and the form moves on", async ({
    page,
  }) => {
    const storm = await openTrudy(page, "2026-10-15T13:20:00Z");
    await expectShowing(page, "20261015_06Z", "20261015_06Z");
    await expect(page.getByTestId("pending-cycle")).toContainText(
      "scheduled for 13:30Z",
    );

    storm.cycles.push("20261015_12Z");
    await page.clock.fastForward("15:00"); // 13:35Z
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
    await expect(page.getByTestId("pending-cycle")).toBeHidden();
    // The form's cycle has now run, and it is the one on screen.
    await expectForm(page, "20261015_12Z");
    await expect(page.getByTestId("cycle-exists")).toContainText(
      "20261015_12Z has already run — it's the one shown",
    );
    await expect(
      page.getByTestId("cycle-exists").getByRole("button", { name: "View it" }),
    ).toBeHidden();
    await expect(runButton(page)).toBeDisabled();
  });

  test("the text field, date button and hour select always show the same cycle", async ({
    page,
  }) => {
    await openTrudy(page, "2026-10-15T13:40:00Z");

    await input(page).fill("20261014_18Z");
    await expectForm(page, "20261014_18Z");

    await hour(page).selectOption("0");
    await expectForm(page, "20261014_00Z");

    await dateButton(page).click();
    await page
      .locator('[data-calendar-day][aria-label*="October 12, 2026"]')
      .click();
    await expectForm(page, "20261012_00Z");

    // An hour no cycle runs at: the select must not pretend it's 00Z, and
    // the form says why it won't run.
    await input(page).fill("20261014_07Z");
    await expect(hour(page)).toHaveValue("");
    await expect(page.getByTestId("cycle-input-problem")).toContainText(
      "00, 06, 12 or 18Z",
    );
    await expect(runButton(page)).toBeDisabled();

    // Half-typed: nothing claims a date or an hour.
    await input(page).fill("2026101");
    await expect(dateButton(page)).toHaveText("select date");
    await expect(hour(page)).toHaveValue("");
    await expect(page.getByTestId("cycle-input-problem")).toContainText(
      "YYYYMMDD_HHZ",
    );
    await expect(runButton(page)).toBeDisabled();

    // Picking an hour from there lands on a whole label again.
    await input(page).fill("20261013_18Z");
    await expect(page.getByTestId("cycle-input-problem")).toBeHidden();
    await expectForm(page, "20261013_18Z");
  });

  test("a cycle the storm already has is offered to view, not to run again", async ({
    page,
  }) => {
    // The reported state: latest 12Z, viewing 06Z, the form on 00Z.
    await openTrudy(page, "2026-10-15T13:40:00Z", {
      cycles: [...TRUDY_CYCLES, "20261015_12Z"],
    });
    await chip(page, "20261015_06Z").click();
    await expectShowing(page, "20261015_06Z", "20261015_12Z");

    await input(page).fill("20261015_00Z");
    const exists = page.getByTestId("cycle-exists");
    await expect(exists).toContainText("20261015_00Z has already run");
    await expect(runButton(page)).toBeDisabled();
    await exists.getByRole("button", { name: "View it" }).click();

    await expectShowing(page, "20261015_00Z", "20261015_12Z");
    await expect(exists).toContainText("it's the one shown");
  });

  test("a past cycle that won't load says so, and doesn't pretend to be on screen", async ({
    page,
  }) => {
    await openTrudy(page, "2026-10-15T13:40:00Z", {
      cycles: [...TRUDY_CYCLES, "20261015_12Z"],
      failCycle: ["20261014_18Z"],
    });
    await expectShowing(page, "20261015_12Z", "20261015_12Z");

    await chip(page, "20261014_18Z").click();
    await expect(banner(page)).toContainText("R2 unavailable");
    await expectShowing(page, "20261015_12Z", "20261015_12Z");

    // The next view that works clears the stale error.
    await chip(page, "20261015_06Z").click();
    await expectShowing(page, "20261015_06Z", "20261015_12Z");
    await expect(banner(page)).toBeHidden();
  });

  test("moving to another storm starts it fresh, and going back starts the first one fresh too", async ({
    page,
  }) => {
    const trudy = stormFixture("EP212026", "Trudy", "2026-10-15T12:00:00Z", [
      ...TRUDY_CYCLES,
      "20261015_12Z",
    ]);
    const vince = stormFixture("AL142026", "Vince", "2026-10-15T06:00:00Z", [
      "20261014_18Z",
      "20261015_00Z",
    ]);
    await serve(page, [trudy, vince], ["20261014_12Z"]);
    await page.clock.install({ time: new Date("2026-10-15T09:00:00Z") });
    await page.goto("/storms/EP212026");
    await expect(context(page)).toBeVisible({ timeout: 15_000 });

    // Leave every kind of per-storm state behind.
    await chip(page, "20261014_06Z").click();
    await expectShowing(page, "20261014_06Z", "20261015_12Z");
    await chip(page, "20261014_12Z").click(); // fails: leaves an error up
    await expect(banner(page)).toBeVisible();
    await input(page).fill("20261013_18Z");
    await page.locator("#coastline-lat-input").fill("25.5");
    await page.locator("#members-input").fill("7");

    // A client-side link to the other storm -- the same route, so the page
    // component is reused rather than mounted afresh.
    await page.evaluate(() => {
      const a = document.createElement("a");
      a.href = "/storms/AL142026";
      a.textContent = "go to AL142026";
      a.id = "storm-switch";
      document.body.append(a);
    });
    await page.locator("#storm-switch").click();
    await expect(page).toHaveURL(/\/storms\/AL142026$/);

    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "AL142026 Vince",
    );
    await expectShowing(page, "20261015_00Z", "20261015_00Z");
    await expect(banner(page)).toBeHidden();
    await expectForm(page, "20261015_06Z");
    await expect(page.locator("#coastline-lat-input")).toHaveValue("");
    await expect(page.locator("#members-input")).toHaveValue("50");

    // Browser back: Trudy again, on her latest, nothing from before.
    await page.goBack();
    await expect(page).toHaveURL(/\/storms\/EP212026$/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "EP212026 Trudy",
    );
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
    await expect(banner(page)).toBeHidden();
  });

  test("an archive storm's form starts inside its own track, not at today's date", async ({
    page,
  }) => {
    // Its last fix was months ago: today's label is outside its track, and
    // the API would refuse it. The form offers its newest cycle not yet run.
    const old = stormFixture(
      "AL052026",
      "Edouard",
      "2026-08-20T18:00:00Z",
      ["20260820_06Z", "20260820_18Z"],
      { active: false },
    );
    await serve(page, [old]);
    await page.clock.install({ time: new Date("2026-10-15T13:40:00Z") });
    await page.goto("/storms/AL052026");
    await expect(context(page)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("pending-cycle")).toBeHidden();
    await expectForm(page, "20260820_12Z");
    await expect(runButton(page)).toBeEnabled();
  });

  test("on a phone, everything fits the screen and the states still agree", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openTrudy(page, "2026-10-15T13:40:00Z", {
      cycles: [...TRUDY_CYCLES, "20261015_12Z"],
      failCycle: ["20261014_12Z"],
    });
    await chip(page, "20261015_06Z").click();
    await expectShowing(page, "20261015_06Z", "20261015_12Z");
    await input(page).fill("20261015_00Z");
    await expect(page.getByTestId("cycle-exists")).toBeVisible();
    await chip(page, "20261014_12Z").click();
    await expect(banner(page)).toBeVisible();

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth -
        document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    await page.screenshot({
      path: test.info().outputPath("storm-page-mobile.png"),
      fullPage: true,
    });
  });
});

test.describe("a signed-in forecaster running a cycle", () => {
  test.beforeEach(async ({ page }) => {
    await signUpViaMagicLink(
      page,
      `run-${Date.now()}-${Math.random()}@example.com`,
    );
  });

  test("a sign-in link brings them back to a page on this site, never anywhere else", async ({
    page,
  }) => {
    await serve(page, [
      stormFixture("EP212026", "Trudy", "2026-10-15T12:00:00Z", TRUDY_CYCLES),
    ]);
    await page.goto("/auth/login?next=%2Fstorms%2FEP212026");
    await expect(page).toHaveURL(/\/storms\/EP212026$/, { timeout: 15_000 });

    for (const next of [
      "//evil.example",
      "https://evil.example/",
      "/\\evil.example",
    ]) {
      await page.goto(`/auth/login?next=${encodeURIComponent(next)}`);
      await expect(page).toHaveURL(/\/profile$/, { timeout: 15_000 });
    }
  });

  test("runs the pending cycle, watches it run, and is shown it as soon as it exists", async ({
    page,
  }) => {
    // 13:45Z: 12Z is due but hasn't appeared; the forecaster runs it.
    const storm = await openTrudy(page, "2026-10-15T13:45:00Z");
    await expect(page.getByTestId("sign-in-to-run")).toBeHidden();
    await expectForm(page, "20261015_12Z");
    const runs = await answerRuns(page, storm, ["ran"]);

    await page.locator("#members-input").fill("80"); // more than the API allows
    await page.locator("#coastline-lat-input").fill("25.5");
    await page.locator("#coastline-lon-input").fill("-110.2");
    runs.hold();
    await runButton(page).click();

    // While it runs: one clear "Running…", and the screen hasn't jumped.
    await expect(page.getByRole("button", { name: "Running…" })).toBeDisabled();
    await expectShowing(page, "20261015_06Z", "20261015_06Z");

    runs.release();
    await expect(page.getByRole("button", { name: "Running…" })).toBeHidden();
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
    await expect(page.getByTestId("manual-run")).toBeVisible();
    await expect(page.getByTestId("cycle-exists")).toContainText(
      "20261015_12Z has already run — it's the one shown",
    );
    await expect(banner(page)).toBeHidden();

    // What was sent is what the form showed, members capped at the maximum.
    expect(runs.sent).toEqual([
      {
        cycle: "20261015_12Z",
        members: 50,
        worst_case: false,
        coastline_lat: 25.5,
        coastline_lon: -110.2,
      },
    ]);
    await expect(page.locator("#members-input")).toHaveValue("50");
  });

  test("a run refused because the schedule hasn't reached it says when, and leaves everything as it was", async ({
    page,
  }) => {
    const storm = await openTrudy(page, "2026-10-15T12:50:00Z");
    await answerRuns(page, storm, [
      {
        status: 409,
        code: "not_scheduled_yet",
        detail:
          "the 20261015_12Z cycle runs automatically at 13:30Z, once its vitals have landed; a manual run before then would replace it",
      },
    ]);
    await page.locator("#coastline-lat-input").fill("25.5");
    await runButton(page).click();

    await expect(banner(page)).toContainText("runs automatically at 13:30Z");
    await expectShowing(page, "20261015_06Z", "20261015_06Z");
    await expectForm(page, "20261015_12Z");
    await expect(page.locator("#coastline-lat-input")).toHaveValue("25.5");
    await expect(runButton(page)).toBeEnabled();

    // The cron runs it; the next poll shows it and the banner has gone.
    storm.cycles.push("20261015_12Z");
    await page.clock.fastForward("45:00"); // 13:35Z
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
    await expect(banner(page)).toBeHidden();
  });

  test("a run that fails says so, keeps what they entered, and works when tried again", async ({
    page,
  }) => {
    const storm = await openTrudy(page, "2026-10-15T13:45:00Z");
    const runs = await answerRuns(page, storm, [
      { status: 500, detail: "inference container unavailable" },
      "ran",
    ]);
    await page.locator("#members-input").fill("20");
    await runButton(page).click();

    await expect(banner(page)).toContainText(
      "500: inference container unavailable",
    );
    await expectShowing(page, "20261015_06Z", "20261015_06Z");
    await expectForm(page, "20261015_12Z");
    await expect(page.locator("#members-input")).toHaveValue("20");

    await runButton(page).click();
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
    await expect(banner(page)).toBeHidden();
    expect(runs.sent.map((b) => [b.cycle, b.members])).toEqual([
      ["20261015_12Z", 20],
      ["20261015_12Z", 20],
    ]);
  });

  test("moving to another storm while a run is in flight leaves the new storm's page alone", async ({
    page,
  }) => {
    // Found by Copilot review on #217: the run's result was assigned before
    // the storm-switch check, so it landed on whichever storm was open.
    const trudy = stormFixture("EP212026", "Trudy", "2026-10-15T12:00:00Z", [
      ...TRUDY_CYCLES,
    ]);
    const vince = stormFixture("AL142026", "Vince", "2026-10-15T12:00:00Z", [
      "20261015_00Z",
      "20261015_06Z",
    ]);
    await serve(page, [trudy, vince]);
    const runs = await answerRuns(page, trudy, ["ran"]);
    await page.clock.install({ time: new Date("2026-10-15T13:45:00Z") });
    await page.goto("/storms/EP212026");
    await expect(context(page)).toBeVisible({ timeout: 15_000 });

    runs.hold();
    await runButton(page).click();
    await expect(page.getByRole("button", { name: "Running…" })).toBeVisible();

    await page.evaluate(() => {
      const a = document.createElement("a");
      a.href = "/storms/AL142026";
      a.id = "storm-switch";
      a.textContent = "go to AL142026";
      document.body.append(a);
    });
    await page.locator("#storm-switch").click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "AL142026 Vince",
    );
    await expectShowing(page, "20261015_06Z", "20261015_06Z");
    // Vince isn't running anything: his form is ready to use.
    await expect(runButton(page)).toBeEnabled();

    runs.release();
    await expect.poll(() => trudy.cycles.includes("20261015_12Z")).toBe(true);
    await page.waitForTimeout(300); // let the finished run's handler settle
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "AL142026 Vince",
    );
    await expectShowing(page, "20261015_06Z", "20261015_06Z");
    await expect(page.getByTestId("manual-run")).toBeHidden();
    await expect(banner(page)).toBeHidden();

    // Trudy's run did happen, and is there when the user goes back.
    await page.goBack();
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
  });

  test("a 409 for a cycle that already exists turns into a way to view it, and clears on edit", async ({
    page,
  }) => {
    // The page's copy of the storm predates the 12Z run (the cron finished
    // a moment ago), so the form still allows it.
    const storm = await openTrudy(page, "2026-10-15T13:40:00Z");
    await expectForm(page, "20261015_12Z");
    await page.route("**/v1/storms/EP212026/cycles", (r) => {
      if (r.request().method() !== "POST") return r.fallback();
      storm.cycles.push("20261015_12Z");
      return r.fulfill({
        status: 409,
        json: {
          detail:
            "EP212026 already has a 20261015_12Z cycle (scheduled run); pick it from Past cycles instead of running it again",
          code: "exists",
        },
      });
    });
    await runButton(page).click();

    await expect(banner(page)).toContainText(
      "already has a 20261015_12Z cycle",
    );
    // The page re-read the storm: the cycle is listed, and the form offers it.
    await expect(chip(page, "20261015_12Z")).toBeVisible();
    const exists = page.getByTestId("cycle-exists");
    await expect(exists).toContainText("20261015_12Z has already run");
    await expect(runButton(page)).toBeDisabled();

    // 18Z hasn't begun at 13:40Z, so the picker doesn't offer it.
    await expect(hour(page).locator('option[value="18"]')).toBeDisabled();

    // Changing the cycle to run is moving on from that error.
    await input(page).fill("20261012_00Z");
    await expect(banner(page)).toBeHidden();
    await expectForm(page, "20261012_00Z");
    await expect(exists).toBeHidden();

    // Back to 12Z, and on to the cycle that exists.
    await input(page).fill("20261015_12Z");
    await exists.getByRole("button", { name: "View it" }).click();
    await expectShowing(page, "20261015_12Z", "20261015_12Z");
  });
});
