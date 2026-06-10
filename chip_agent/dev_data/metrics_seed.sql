CREATE TABLE IF NOT EXISTS project_metrics (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    wns FLOAT NOT NULL,
    tns FLOAT NOT NULL,
    power FLOAT NOT NULL,
    area FLOAT NOT NULL
);

-- Seed data for Proj_A and Proj_B
INSERT INTO project_metrics (project_id, metric_date, wns, tns, power, area) VALUES
('Proj_A', '2026-06-01', -0.12, -4.50, 1.25, 4.50),
('Proj_A', '2026-06-05', -0.05, -1.20, 1.28, 4.50),
('Proj_A', '2026-06-10', 0.02, 0.00, 1.30, 4.50),
('Proj_B', '2026-06-01', -0.25, -12.30, 0.45, 1.80),
('Proj_B', '2026-06-05', -0.10, -3.10, 0.46, 1.80),
('Proj_B', '2026-06-10', -0.02, -0.40, 0.48, 1.80);
