import { expect, test } from "@playwright/test";
import { initialData, type BoardData } from "../src/lib/kanban";

const cloneBoard = (board: BoardData = initialData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;

const login = async (page: import("@playwright/test").Page) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

test("requires login before showing board", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).not.toBeVisible();
});

test("loads the kanban board after login", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("persists a new card after refresh", async ({ page }) => {
  await login(page);
  const cardTitle = `Persisted card ${Date.now()}`;
  const firstColumn = page.locator('[data-testid^="column-"]').first();

  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByPlaceholder("Details").fill("Stored in SQLite.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(cardTitle)).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.getByText(cardTitle)).toBeVisible();
});

test("moves a card into an emptied column", async ({ page }) => {
  await login(page);
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-discovery");

  await targetColumn
    .locator('button[aria-label="Delete Prototype analytics view"]')
    .click();
  await expect(targetColumn.getByTestId("card-card-3")).not.toBeVisible();

  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + columnBox.height / 2,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await login(page);
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("updates the board from an AI chat response", async ({ page }) => {
  const aiCardTitle = `AI e2e card ${Date.now()}`;
  const aiBoard = cloneBoard();
  aiBoard.cards["card-ai-e2e"] = {
    id: "card-ai-e2e",
    title: aiCardTitle,
    details: "Edited by mocked AI.",
  };
  aiBoard.columns[3].cardIds.push("card-ai-e2e");

  await page.route("**/api/ai/chat", async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({
      message: `Create, edit, and move ${aiCardTitle}`,
    });

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assistant_message: "I created, edited, and moved the card.",
        operations: [
          {
            type: "create_card",
            card_id: "card-ai-e2e",
            column_id: "col-backlog",
            title: aiCardTitle,
            details: "Created by mocked AI.",
          },
          {
            type: "update_card",
            card_id: "card-ai-e2e",
            details: "Edited by mocked AI.",
          },
          {
            type: "move_card",
            card_id: "card-ai-e2e",
            target_column_id: "col-review",
          },
        ],
        board: aiBoard,
      }),
    });
  });

  await login(page);
  await page.getByLabel("Message AI").fill(`Create, edit, and move ${aiCardTitle}`);
  await page.getByRole("button", { name: /send/i }).click();

  const reviewColumn = page.getByTestId("column-col-review");
  await expect(reviewColumn.getByText(aiCardTitle)).toBeVisible();
  await expect(reviewColumn.getByText("Edited by mocked AI.")).toBeVisible();
  await expect(page.getByText("I created, edited, and moved the card.")).toBeVisible();
});

test("keeps the board unchanged when AI returns no operations", async ({ page }) => {
  const board = cloneBoard();

  await page.route("**/api/board", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(board),
    });
  });
  await page.route("**/api/ai/chat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assistant_message: "No changes needed.",
        operations: [],
        board,
      }),
    });
  });

  await login(page);
  await expect(page.locator('[data-testid^="card-"]')).toHaveCount(8);

  await page.getByLabel("Message AI").fill("Summarize the board");
  await page.getByRole("button", { name: /send/i }).click();

  await expect(page.getByText("No changes needed.")).toBeVisible();
  await expect(page.locator('[data-testid^="card-"]')).toHaveCount(8);
});

test("can log out", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});
