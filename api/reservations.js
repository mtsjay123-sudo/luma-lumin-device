// api/reservations.js
export default async function handler(req, res) {
    if (req.method !== 'GET') {
        return res.status(405).json({ message: 'Method Not Allowed' });
    }

    const SUPABASE_URL = process.env.SUPABASE_URL;
    const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY;

    if (SUPABASE_URL && SUPABASE_KEY) {
        try {
            const response = await fetch(`${SUPABASE_URL}/rest/v1/reservations?select=*&order=timestamp.desc`, {
                method: 'GET',
                headers: {
                    'apikey': SUPABASE_KEY,
                    'Authorization': `Bearer ${SUPABASE_KEY}`
                }
            });

            if (!response.ok) {
                return res.status(500).json({ message: 'Error fetching from Supabase' });
            }

            const data = await response.json();
            return res.status(200).json(data);
        } catch (err) {
            return res.status(500).json({ message: 'Internal Server error' });
        }
    }

    // Fallback for demo
    return res.status(200).json([
        { email: 'demo@example.com', phone: '123-456-7890', timestamp: new Date().toISOString() }
    ]);
}
