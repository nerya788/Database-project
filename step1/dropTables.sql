-- Active: 1780913150388@@127.0.0.1@3306
-- =============================================================
-- Project: School Football League Database System
-- Script: dropTables.sql
-- Description: Drops the 7 core tables in the correct order 
--              to avoid foreign key constraint conflicts.
-- =============================================================
USE school_football_db;

-- Drop dependent tables first
DROP TABLE IF EXISTS Match_Events;
DROP TABLE IF EXISTS Maintenance_Logs;
DROP TABLE IF EXISTS Medical_Kits;
DROP TABLE IF EXISTS Training_Gear;
DROP TABLE IF EXISTS Matches;
DROP TABLE IF EXISTS Practices;
DROP TABLE IF EXISTS Global_Equipment;
DROP TABLE IF EXISTS Teams;
DROP TABLE IF EXISTS Students;
DROP TABLE IF EXISTS Fields;
DROP TABLE IF EXISTS Schools;

-- COMMIT is often implicit in DDL, but good practice in some environments
COMMIT;