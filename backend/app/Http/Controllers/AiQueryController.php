<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class AiQueryController extends Controller
{
    /**
     * Execute a SELECT-only SQL query from the AI service.
     *
     * POST /api/ai/query
     * Body: { "sql": "SELECT ..." }
     */
    public function execute(Request $request)
    {
        $request->validate([
            'sql' => 'required|string|max:2000',
        ]);

        $sql = trim($request->input('sql'));

        // ---- SAFETY: Only allow SELECT queries ----
        $normalizedSql = strtoupper($sql);

        // Must start with SELECT or WITH (for CTEs)
        if (!preg_match('/^\s*(SELECT|WITH)\s/i', $sql)) {
            return response()->json([
                'error' => 'Only SELECT queries are allowed.',
            ], 403);
        }

        // Block dangerous keywords
        $dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC'];
        foreach ($dangerous as $keyword) {
            if (preg_match('/\b' . $keyword . '\b/i', $sql)) {
                return response()->json([
                    'error' => "Forbidden SQL keyword detected: {$keyword}",
                ], 403);
            }
        }

        // ---- Execute the query ----
        try {
            Log::info('AI Query executing SQL', ['sql' => $sql]);

            // Set a 5-second query timeout
            DB::statement("SET SESSION MAX_EXECUTION_TIME = 5000");

            $results = DB::select($sql);

            // Convert to plain arrays
            $data = array_map(function ($row) {
                return (array) $row;
            }, $results);

            Log::info('AI Query result', ['row_count' => count($data)]);

            return response()->json([
                'data' => $data,
                'row_count' => count($data),
            ]);

        } catch (\Exception $e) {
            Log::error('AI Query failed', [
                'sql' => $sql,
                'error' => $e->getMessage(),
            ]);

            return response()->json([
                'error' => 'Query execution failed: ' . $e->getMessage(),
            ], 500);
        }
    }
}
