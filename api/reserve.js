// api/reserve.js
export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ message: 'Method Not Allowed' });
    }

    const { email, phone, timestamp } = req.body;

    // IMPORTANT: For production, you would connect to Supabase/PostgreSQL here.
    // For now, we will return success to allow the UI to work.
    // To enable permanent storage, you'll need to set up a Supabase project.

    const SUPABASE_URL = process.env.SUPABASE_URL;
    const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY;

    if (SUPABASE_URL && SUPABASE_KEY) {
        try {
            const response = await fetch(`${SUPABASE_URL}/rest/v1/reservations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'apikey': SUPABASE_KEY,
                    'Authorization': `Bearer ${SUPABASE_KEY}`,
                    'Prefer': 'return=minimal'
                },
                body: JSON.stringify({ email, phone, timestamp })
            });

            if (!response.ok) {
                const error = await response.text();
                console.error('Supabase Error:', error);
                return res.status(500).json({ status: 'error', message: 'Database error' });
            }

            return res.status(200).json({ status: 'success', message: 'Saved to Supabase' });
        } catch (err) {
            console.error('Fetch Error:', err);
            return res.status(500).json({ status: 'error', message: 'Internal Server Error' });
        }
    }

    // Fallback for demo if no DB is connected yet
    console.log('Demo mode: Reservation received:', { email, phone });
    return res.status(200).json({
        status: 'success',
        message: 'Reservation received (Demo Mode - No Database Connected)'
    });
}
