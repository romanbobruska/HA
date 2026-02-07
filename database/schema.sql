CREATE TABLE "own_energy_prices_total"      (
  "day" VARCHAR(20) NOT NULL,
  "hour" INTEGER NOT NULL,
  "minute" INTEGER NOT NULL,
  "priceCZKhourBuy" REAL NOT NULL,
  "priceCZKhourProd" REAL NOT NULL,
  "priceCZKquarterBuy" REAL NOT NULL,
  "priceCZKquarterProd" REAL NOT NULL,
  "levelCheapestHourBuy" INTEGER,
  "levelCheapestQuarterBuy" INTEGER,
  "levelMostExpensiveHourProd" INTEGER,
  "levelMostExpensiveQuarterProd" INTEGER
)