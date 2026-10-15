import { readFileSync } from "node:fs";
import { test, expect, type Page } from "@playwright/test";
import { signUpViaMagicLink } from "./helpers/auth";

// The storm page holds several views of "which cycle": the one on screen
// (cycle-context panel, map, highlighted Past-cycles chip), the one the
// "Run a new cycle" form would run (#cycle-input, the date button and the
// hour select), and the error banner from whatever was last tried. They
// drifted apart (reported on EP212026 Trudy, 15 Oct 2026): viewing 06Z with
// 12Z the latest, the form still offered 00Z -- a label the storm already
// had, typed in by nobody -- and running it left a 409 banner that nothing
// cleared. These pin the clock and the storms, so every state is exact.

// Mocked end to end (no demo API), so CI runs this against the built Worker
// too (playwright.workerd.config.ts): a demo storm and cycle as templates.
const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/storm-page.json", import.meta.url), "utf8"),
) as { storm: Record<string, unknown>; cycle: Record<string, unknown> };

type Storm = Record<string, unknown> & { storm_id: string; cycles: string[] };

function stormFixture(
  base: Record<string, unknown>,
  stormId: string,
  name: string,
  fixIso: string,
  cycles: string[],
): Storm {
  const real = base as {
    latest_fix: Record<string, unknown>;
    history: unknown[];
  };
  const fix = { ...real.latest_fix, valid_time: fixIso };
  return {
    ...base,
    storm_id: stormId,
    name,
    basin: stormId.slice(0, 2),
    trained_basin: stormId.startsWith("AL"),
    active: true,
    season: 2026,
    latest_fix: fix,
    history: [...real.history.slice(0, -1), fix],
    cycles: [...cycles],
    last_cycle: cycles.at(-1) ?? null,
  };
}

/** Serves `storms` (mutable: tests add cycles to them mid-test) and any of
 * their cycles from the template; `failCycle` labels answer 500. */
async function serve(page: Page, storms: Storm[], failCycle: string[] = []) {
  const { cycle } = fixture;
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
      const c = cycle as { payload: Record<string, unknown> };
      return r.fulfill({
        json: {
          ...cycle,
          payload: { ...c.payload, cycle: label, storm_id: storm.storm_id },
        },
      });
    });
  }
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

async function trudy(page: Page, nowIso: string, cycles = TRUDY_CYCLES) {
  const s = stormFixture(
    fixture.storm,
    "EP212026",
    "Trudy",
    "2026-10-15T12:00:00Z",
    cycles,
  );
  await serve(page, [s]);
  await page.clock.install({ time: new Date(nowIso) });
  await page.goto(`/storms/${s.storm_id}`);
  await expect(page.getByTestId("cycle-context")).toBeVisible({
    timeout: 15_000,
  });
  return s;
}

const input = (page: Page) => page.locator("#cycle-input");
const hour = (page: Page) => page.locator("#cycle-hour-select");
const dateButton = (page: Page) => page.getByTestId("cycle-date-trigger");
const runButton = (page: Page) =>
  page.getByRole("button", { name: /^Run cycle$|^Running…$/ });
const banner = (page: Page) => page.getByTestId("page-error");
const chip = (page: Page, label: string) =>
  page
    .getByTestId("past-cycles")
    .getByRole("button", { name: label, exact: true });

async function expectForm(page: Page, label: string) {
  await expect(input(page)).toHaveValue(label);
  await expect(dateButton(page)).toHaveText(label.slice(0, 8));
  await expect(hour(page)).toHaveValue(String(Number(label.slice(9, 11))));
}

test("the cycle to run follows the clock until the user picks one", async ({
  page,
}) => {
  // 12:50Z: the 12Z cycle is on the calendar but not run yet (due 13:30Z).
  const storm = await trudy(page, "2026-10-15T12:50:00Z");
  await expectForm(page, "20261015_12Z");
  await expect(runButton(page)).toBeEnabled();

  // The page sits open into the evening. The cron has run 12Z, and the
  // form moves on with the clock rather than offering 12Z again.
  storm.cycles.push("20261015_12Z");
  await page.clock.fastForward("05:20:00"); // 18:10Z, polls reload
  await expectForm(page, "20261015_18Z");

  // Once the user picks a cycle, a poll never moves it.
  await hour(page).selectOption("6");
  await page.locator("#cycle-input").fill("20261014_06Z");
  await expectForm(page, "20261014_06Z");
  await page.clock.fastForward("06:00:00");
  await expectForm(page, "20261014_06Z");
});

test("the text field, date button and hour select always show the same cycle", async ({
  page,
}) => {
  await trudy(page, "2026-10-15T13:40:00Z");

  await input(page).fill("20261014_18Z");
  await expectForm(page, "20261014_18Z");

  await hour(page).selectOption("0");
  await expectForm(page, "20261014_00Z");

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
});

test("a cycle the storm already has is offered to view, not run again", async ({
  page,
}) => {
  // The screenshot: latest 12Z, viewing 06Z, the form on 00Z.
  await trudy(page, "2026-10-15T13:40:00Z", [...TRUDY_CYCLES, "20261015_12Z"]);
  await chip(page, "20261015_06Z").click();
  await expect(page.getByTestId("cycle-context")).toContainText(
    "Showing forecast cycle 20261015_06Z",
  );

  // 13:40Z: the 12Z cycle exists, so the default is already run.
  await expectForm(page, "20261015_12Z");
  await expect(page.getByTestId("cycle-exists")).toContainText(
    "20261015_12Z has already run",
  );
  await expect(runButton(page)).toBeDisabled();

  await input(page).fill("20261015_00Z");
  const exists = page.getByTestId("cycle-exists");
  await expect(exists).toContainText("20261015_00Z has already run");
  await exists.getByRole("button", { name: "View it" }).click();

  // Every view of "which cycle" now agrees.
  await expect(page.getByTestId("cycle-context")).toContainText(
    "Showing forecast cycle 20261015_00Z",
  );
  await expect(chip(page, "20261015_00Z")).toHaveAttribute(
    "aria-current",
    "true",
  );
  await expect(chip(page, "20261015_06Z")).not.toHaveAttribute(
    "aria-current",
    "true",
  );
  await expect(page.getByText(/Viewing an older cycle/)).toBeVisible();
});

test("a past cycle that fails to load doesn't leave its chip selected", async ({
  page,
}) => {
  const base = fixture.storm;
  const s = stormFixture(base, "EP212026", "Trudy", "2026-10-15T12:00:00Z", [
    ...TRUDY_CYCLES,
    "20261015_12Z",
  ]);
  await serve(page, [s], ["20261014_18Z"]);
  await page.clock.install({ time: new Date("2026-10-15T13:40:00Z") });
  await page.goto(`/storms/${s.storm_id}`);
  const context = page.getByTestId("cycle-context");
  await expect(context).toContainText("Showing forecast cycle 20261015_12Z", {
    timeout: 15_000,
  });

  await chip(page, "20261014_18Z").click();
  await expect(banner(page)).toContainText("R2 unavailable");
  // Still showing 12Z, and saying so everywhere.
  await expect(context).toContainText("Showing forecast cycle 20261015_12Z");
  await expect(chip(page, "20261015_12Z")).toHaveAttribute(
    "aria-current",
    "true",
  );
  await expect(chip(page, "20261014_18Z")).not.toHaveAttribute(
    "aria-current",
    "true",
  );
  await expect(page.getByText(/Viewing an older cycle/)).toBeHidden();

  // The next view that works clears the stale error.
  await chip(page, "20261015_06Z").click();
  await expect(context).toContainText("Showing forecast cycle 20261015_06Z");
  await expect(banner(page)).toBeHidden();
});

test("a 409 for a cycle that already exists turns into a way to view it, and clears on edit", async ({
  page,
}) => {
  await signUpViaMagicLink(page, `sync-${Date.now()}@example.com`);
  // The page's copy of the storm predates the 12Z run (another visitor's
  // view, or the cron finishing a moment ago), so the form allows it.
  const storm = await trudy(page, "2026-10-15T13:40:00Z");
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

  await expect(banner(page)).toContainText("already has a 20261015_12Z cycle");
  // The page re-read the storm: the new cycle is listed, and the form
  // knows it exists.
  await expect(chip(page, "20261015_12Z")).toBeVisible();
  await expect(page.getByTestId("cycle-exists")).toContainText(
    "20261015_12Z has already run",
  );

  // Changing the cycle to run is moving on from that error.
  await hour(page).selectOption("6");
  await expect(banner(page)).toBeHidden();
});

test("moving to another storm starts it fresh, with nothing carried over", async ({
  page,
}) => {
  const base = fixture.storm;
  const trudyStorm = stormFixture(
    base,
    "EP212026",
    "Trudy",
    "2026-10-15T12:00:00Z",
    [...TRUDY_CYCLES, "20261015_12Z"],
  );
  const other = stormFixture(
    base,
    "AL142026",
    "Vince",
    "2026-10-15T06:00:00Z",
    ["20261014_18Z", "20261015_00Z"],
  );
  await serve(page, [trudyStorm, other], ["20261014_12Z"]);
  await page.clock.install({ time: new Date("2026-10-15T09:00:00Z") });
  await page.goto("/storms/EP212026");
  const context = page.getByTestId("cycle-context");
  await expect(context).toContainText("Showing forecast cycle 20261015_12Z", {
    timeout: 15_000,
  });

  await chip(page, "20261014_06Z").click();
  await expect(context).toContainText("Showing forecast cycle 20261014_06Z");
  await chip(page, "20261014_12Z").click(); // fails: leaves an error up
  await expect(banner(page)).toBeVisible();
  await input(page).fill("20261013_18Z");
  await page.locator("#coastline-lat-input").fill("25.5");
  await page.locator("#members-input").fill("7");

  // A client-side navigation to the other storm -- the same route, so the
  // page component is reused rather than mounted afresh.
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
    "AL142026",
  );
  await expect(context).toContainText("Showing forecast cycle 20261015_00Z");
  await expect(context).toContainText("the latest run");
  await expect(chip(page, "20261015_00Z")).toHaveAttribute(
    "aria-current",
    "true",
  );
  await expect(page.getByText(/Viewing an older cycle/)).toBeHidden();
  await expect(banner(page)).toBeHidden();
  await expectForm(page, "20261015_06Z");
  await expect(page.locator("#coastline-lat-input")).toHaveValue("");
  await expect(page.locator("#members-input")).toHaveValue("50");
});

test("an archive storm's form starts inside its own track, not at today's date", async ({
  page,
}) => {
  // A storm whose last fix was months ago: today's synoptic label is
  // outside its track and the API would refuse it (400). The default is
  // its newest cycle it doesn't have yet.
  const base = fixture.storm;
  const old = {
    ...stormFixture(base, "AL052026", "Edouard", "2026-08-20T18:00:00Z", [
      "20260820_06Z",
      "20260820_18Z",
    ]),
    active: false,
  };
  await serve(page, [old]);
  await page.clock.install({ time: new Date("2026-10-15T13:40:00Z") });
  await page.goto("/storms/AL052026");
  await expect(page.getByTestId("cycle-context")).toBeVisible({
    timeout: 15_000,
  });
  await expectForm(page, "20260820_12Z");
  await expect(runButton(page)).toBeEnabled();
});
