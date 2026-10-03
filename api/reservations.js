// api/reservations.js: the waitlist, for the admin page only.
import { isAdmin } from "./_lib/admin-auth.js";

export default async function handler(req, res, env = process.env, fetchImpl = fetch) {
    res.setHeader('Cache-Control', 'no-store');
    if (req.method !== 'GET') {
        return res.status(405).json({ message: 'Method Not Allowed' });
    }
    if (!isAdmin(req, env)) {
        return res.status(401).json({ message: 'Admin sign-in required' });
    }
    const SUPABASE_URL = env.SUPABASE_URL;
    const SUPABASE_KEY = env.SUPABASE_SERVICE_ROLE_KEY;
    if (!SUPABASE_URL || !SUPABASE_KEY) {
        return res.status(503).json({ message: 'Waitlist storage is not configured' });
    }
    try {
        const response = await fetchImpl(`${SUPABASE_URL}/rest/v1/reservations?select=email,phone,timestamp&order=timestamp.desc`, {
            method: 'GET',
            headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }
        });
        if (!response.ok) {
            return res.status(502).json({ message: 'Error fetching from Supabase' });
        }
        return res.status(200).json(await response.json());
    } catch (err) {
        return res.status(500).json({ message: 'Internal Server error' });
    }
}
