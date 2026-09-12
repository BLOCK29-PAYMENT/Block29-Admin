-- 005: Deactivate the legacy admin account whose credentials were printed on
-- the old public login page (admin@salonbookin.com / admin123).
-- Requires migration 001 (is_active column). Reversible (set is_active=1).
UPDATE users SET is_active = 0 WHERE email = 'admin@salonbookin.com';
