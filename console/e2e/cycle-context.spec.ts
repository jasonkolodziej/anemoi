import { test, expect, type Page } from "@playwright/test";

// At 07:00Z the 06Z cycle exists on the calendar, but the cron only runs it
// at 07:30Z (t+1:30), so the newest forecast is still 00Z while the storm's
// latest fix is already 06Z -- and the run form defaults to 06Z. The page
// used to say none of this: the only hint of which cycle was on screen was a
// highlighted chip at the bottom of the page. These pin the clock and the
// storm to exactly that moment.

const API = "http://127.0.0.1:8000";

async function stormAt(
  page: Page,
  request: import("@playwright/test").APIRequestContext,
  nowIso: string,
) {
  const storms = await (await request.get(`${API}/v1/storms`)).json();
  const stormId: string = storms[0].storm_id;
  const real = await (await request.get(`${API}/v1/storms/${stormId}`)).json();
  const ran = await request.post(`${API}/v1/storms/${stormId}/cycles`, {
    data: { cycle: "20261008_00Z", members: 10 },
  });
  expect(ran.ok()).toBeTruthy();
  const cycle = await ran.json();

  const fix = { ...real.latest_fix, valid_time: "2026-10-08T06:00:00Z" };
  const storm = {
    ...real,
    active: true,
    latest_fix: fix,
    history: [...real.history.slice(0, -1), fix],
    cycles: ["20261007_18Z", "20261008_00Z"],
    last_cycle: "20261008_00Z",
  };
  await page.route(`**/v1/storms/${stormId}`, (r) =>
    r.fulfill({ json: storm }),
  );
  await page.route(`**/v1/storms/${stormId}/cycles/*`, (r) =>
    r.fulfill({
      json: {
        ...cycle,
        payload: {
          ...cycle.payload,
          cycle: r.request().url().split("/").pop(),
        },
      },
    }),
  );
  await page.clock.install({ time: new Date(nowIso) });
  await page.goto(`/storms/${stormId}`);
  return page.getByTestId("cycle-context");
}

test("the page says which cycle it shows, and that the next one is still to come", async ({
  page,
  request,
}) => {
  const context = await stormAt(page, request, "2026-10-08T07:00:00Z");
  await expect(context).toContainText("Showing forecast cycle 20261008_00Z");
  await expect(context).toContainText("the latest run");
  await expect(context).toContainText(
    "not from the latest fix (2026-10-08 06:00Z)",
  );
  await expect(page.getByTestId("pending-cycle")).toContainText(
    "The 20261008_06Z cycle hasn't run yet — it's scheduled for 07:30Z",
  );
  // The 06Z in the form is visibly a cycle *to run*, not the one shown.
  await expect(page.getByText("Run a new cycle")).toBeVisible();
  await expect(page.locator("#cycle-input")).toHaveValue("20261008_06Z");
});

test("a cycle past its run time reads as running, then overdue", async ({
  page,
  request,
}) => {
  const context = await stormAt(page, request, "2026-10-08T07:40:00Z");
  await expect(context).toBeVisible();
  await expect(page.getByTestId("pending-cycle")).toContainText(
    "should appear within a few minutes",
  );

  await page.clock.fastForward("01:00:00"); // 08:40Z, and the 60s poll reloads
  await expect(page.getByTestId("pending-cycle")).toContainText("is overdue");
});

test("an older cycle picked from the list is called out as older", async ({
  page,
  request,
}) => {
  const context = await stormAt(page, request, "2026-10-08T07:00:00Z");
  await page.getByRole("button", { name: "20261007_18Z" }).click();
  await expect(context).toContainText("Showing forecast cycle 20261007_18Z");
  await expect(context).toContainText(
    "an older run; the latest is 20261008_00Z",
  );
  await context.getByRole("button", { name: "Show latest" }).click();
  await expect(context).toContainText("Showing forecast cycle 20261008_00Z");
});

test("mobile screenshot of the cycle context", async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await stormAt(page, request, "2026-10-08T07:00:00Z");
  await expect(page.getByTestId("pending-cycle")).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("cycle-context-mobile.png"),
    fullPage: false,
  });
});
