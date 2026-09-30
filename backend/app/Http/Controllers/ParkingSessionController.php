<?php

namespace App\Http\Controllers;

use App\Models\ParkingSession;
use App\Models\PaymentReceipt;
use App\Enums\ParkingStatus;
use App\Models\ExitAlert;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;

class ParkingSessionController extends Controller
{
    /**
     * Receive car entry details from the Python LPR system.
     * Creates a new parking session with status ENTER.
     */
    public function carEntry(Request $request)
    {
        $request->validate([
            'license_plate' => 'required|string',
            'color'         => 'required|string',
            'model'         => 'required|string',
            'image'         => 'nullable|image|max:2048', // optional image upload
        ]);

        $imagePath = null;
        if ($request->hasFile('image')) {
            $imagePath = $request->file('image')->store('sessions', 'public');
        }

        $session = ParkingSession::create([
            'license_plate'  => $request->license_plate,
            'color'          => $request->color,
            'model'          => $request->model,
            'entry_time'     => now(),
            'status'         => ParkingStatus::ENTER->value,
            'car_image_path' => $imagePath,
        ]);

        return response()->json($session, 201);
    }

    /**
     * Display a paginated list of parking sessions with optional filters.
     */
    public function index(Request $request)
    {
        $query = ParkingSession::with('paymentReceipts');

        if ($request->filled('search')) {
            $search = $request->query('search');
            $query->where('license_plate', 'like', "%{$search}%");
        }

        if ($request->filled('status')) {
            $query->where('status', strtoupper($request->query('status')));
        }

        if ($request->filled('color')) {
            $query->where('color', $request->query('color'));
        }

        if ($request->filled('model')) {
            $query->where('model', $request->query('model'));
        }

        // Date range filtering — supports both entry_time and exit_time
        $dateField = $request->query('date_field', 'entry_time');
        if (!in_array($dateField, ['entry_time', 'exit_time'])) {
            $dateField = 'entry_time';
        }
        if ($request->filled('date_from')) {
            $dateFrom = $request->query('date_from');
            if ($request->filled('time_from')) {
                // Full datetime comparison when time is provided
                $query->where($dateField, '>=', $dateFrom . ' ' . $request->query('time_from') . ':00');
            } else {
                $query->whereDate($dateField, '>=', $dateFrom);
            }
        }
        if ($request->filled('date_to')) {
            $dateTo = $request->query('date_to');
            if ($request->filled('time_to')) {
                // Full datetime comparison when time is provided
                $query->where($dateField, '<=', $dateTo . ' ' . $request->query('time_to') . ':59');
            } else {
                $query->whereDate($dateField, '<=', $dateTo);
            }
        }
        
        // Default sorting
        $sortField = $request->query('sort_by', 'entry_time');
        $sortOrder = $request->query('sort_order', 'desc');
        
        $query->orderBy($sortField, $sortOrder);

        $sessions = $query->paginate($request->query('per_page', 15));

        // Recalculate amount_due on-the-fly for active ENTER sessions
        // and compute a human-readable duration for all sessions
        $sessions->getCollection()->transform(function ($session) {
            if ($session->status === ParkingStatus::ENTER) {
                $session->amount_due = $session->calculateParkingFee();
            }

            // Compute duration: use exit_time for completed, now() for active
            $endTime = $session->exit_time ?? now();
            $diffMinutes = $session->entry_time->diffInMinutes($endTime);
            $hours = intdiv($diffMinutes, 60);
            $minutes = $diffMinutes % 60;
            $session->duration = "{$hours}h {$minutes}m";

            return $session;
        });

        return response()->json($sessions);
    }

    /**
     * Return distinct color and model values from parking sessions
     * for populating frontend filter dropdowns dynamically.
     */
    public function filterOptions()
    {
        $colors = ParkingSession::select('color')
            ->distinct()
            ->orderBy('color')
            ->pluck('color');

        $models = ParkingSession::select('model')
            ->distinct()
            ->orderBy('model')
            ->pluck('model');

        return response()->json([
            'colors' => $colors,
            'models' => $models,
        ]);
    }

    /**
     * Display the specified parking session with its receipts.
     */
    public function show(string $id)
    {
        $session = ParkingSession::with('paymentReceipts')->findOrFail($id);

        // Recalculate amount_due on-the-fly for active ENTER sessions
        if ($session->status === ParkingStatus::ENTER) {
            $session->amount_due = $session->calculateParkingFee();
        }

        return response()->json($session);
    }

    /**
     * Find the active parking session by license plate (for mobile app).
     * Returns sessions with status ENTER or PAID.
     * For PAID sessions, includes grace/overdue info so the mobile app
     * knows whether to show normal payment or additional payment screen.
     */
    public function findByPlate(string $licensePlate)
    {
        $session = ParkingSession::with('paymentReceipts')
            ->where('license_plate', $licensePlate)
            ->whereIn('status', [ParkingStatus::ENTER->value, ParkingStatus::PAID->value])
            ->orderBy('entry_time', 'desc')
            ->first();

        if (!$session) {
            return response()->json(['message' => 'No active parking session found for this license plate.'], 404);
        }

        // Recalculate amount_due on-the-fly for active ENTER sessions
        if ($session->status === ParkingStatus::ENTER) {
            $session->amount_due = $session->calculateParkingFee();
        }

        $response = $session->toArray();

        // If session is PAID, include grace period info for the mobile app
        if ($session->status === ParkingStatus::PAID) {
            $graceExpired = $session->grace_end_time && now()->greaterThan($session->grace_end_time);

            $response['grace_expired'] = $graceExpired;
            $response['grace_end_time'] = $session->grace_end_time;

            if ($graceExpired) {
                $overdueMinutes = $session->grace_end_time->diffInMinutes(now());
                $overdueHours = max(1, ceil($overdueMinutes / 60));
                $extraCharge = $overdueHours * config('parking.rate_per_hour');

                // Sum of all previous payments
                $totalPaid = $session->paymentReceipts->sum('total_amount');

                $response['overdue_minutes'] = $overdueMinutes;
                $response['extra_charge'] = number_format($extraCharge, 2, '.', '');
                $response['original_fee'] = number_format($session->amount_due, 2, '.', '');
                $response['total_paid'] = number_format($totalPaid, 2, '.', '');
            }
        }

        return response()->json($response);
    }

    /**
     * Process initial payment for a parking session (for mobile app).
     */
    public function pay(Request $request, string $id)
    {
        $request->validate([
            'payment_method' => 'required|string',
        ]);

        $session = ParkingSession::findOrFail($id);

        if ($session->status !== ParkingStatus::ENTER) {
            return response()->json(['message' => 'This session is already paid or completed.'], 400);
        }

        $graceMinutes = config('parking.grace_period_minutes');
        $paymentTime = now();

        // Recalculate and persist the final amount_due at the moment of payment
        $session->amount_due = $session->calculateParkingFee($paymentTime);
        $session->save();

        // Create Payment Receipt
        $receipt = PaymentReceipt::create([
            'parking_session_id' => $session->id,
            'receipt_number'     => 'RCP-' . strtoupper(Str::random(8)),
            'total_amount'       => $session->amount_due,
            'payment_date'       => $paymentTime,
            'payment_method'     => $request->payment_method,
            'payment_type'       => 'initial',
        ]);

        // Update Parking Session: status to PAID and set grace end time
        $session->update([
            'status'         => ParkingStatus::PAID->value,
            'grace_end_time' => $paymentTime->copy()->addMinutes($graceMinutes),
        ]);

        return response()->json([
            'message' => 'Payment successful',
            'receipt' => $receipt,
            'session' => $session->fresh(),
        ]);
    }

    /**
     * Process additional payment when grace period has expired (for mobile app).
     */
    public function payAdditional(Request $request, string $id)
    {
        $request->validate([
            'payment_method' => 'required|string',
        ]);

        $session = ParkingSession::findOrFail($id);

        if ($session->status !== ParkingStatus::PAID) {
            return response()->json(['message' => 'This session is not eligible for additional payment.'], 400);
        }

        // Grace must be expired for additional payment to be valid
        if (!$session->grace_end_time || now()->lessThanOrEqualTo($session->grace_end_time)) {
            return response()->json(['message' => 'Grace period has not expired yet. No additional payment needed.'], 400);
        }

        // Calculate overdue charge
        $overdueMinutes = $session->grace_end_time->diffInMinutes(now());
        $overdueHours = max(1, ceil($overdueMinutes / 60));
        $extraCharge = $overdueHours * config('parking.rate_per_hour');

        $graceMinutes = config('parking.grace_period_minutes');
        $paymentTime = now();

        // Create additional payment receipt (does NOT overwrite the original)
        $receipt = PaymentReceipt::create([
            'parking_session_id' => $session->id,
            'receipt_number'     => 'RCP-' . strtoupper(Str::random(8)),
            'total_amount'       => $extraCharge,
            'payment_date'       => $paymentTime,
            'payment_method'     => $request->payment_method,
            'payment_type'       => 'additional',
        ]);

        // Reset grace period from the additional payment time
        $session->update([
            'grace_end_time' => $paymentTime->copy()->addMinutes($graceMinutes),
        ]);

        return response()->json([
            'message'         => 'Additional payment successful',
            'receipt'         => $receipt,
            'session'         => $session->fresh()->load('paymentReceipts'),
            'overdue_minutes' => $overdueMinutes,
            'extra_charge'    => number_format($extraCharge, 2, '.', ''),
        ]);
    }

    /**
     * Verify car at exit gate (called by Python LPR_exit.py).
     * Handles 5 scenarios including free exits, grace period checks, and attribute mismatch alerts.
     */
    public function carExit(Request $request)
    {
        $request->validate([
            'license_plate' => 'required|string',
            'color'         => 'required|string',
            'model'         => 'required|string',
            'image'         => 'nullable|image|max:2048', // optional image upload
        ]);

        $imagePath = null;
        if ($request->hasFile('image')) {
            $imagePath = $request->file('image')->store('alerts', 'public');
        }

        // Find ANY active session for this license plate
        $session = ParkingSession::where('license_plate', $request->license_plate)
            ->whereIn('status', [ParkingStatus::ENTER->value, ParkingStatus::PAID->value])
            ->orderBy('entry_time', 'desc')
            ->first();

        if (!$session) {
            // Scenario 4: Plate not found
            ExitAlert::create([
                'alert_type'     => 'plate_not_found',
                'license_plate'  => $request->license_plate,
                'detected_color' => $request->color,
                'detected_model' => $request->model,
                'image_path'     => $imagePath,
            ]);

            return response()->json([
                'allowed'    => false,
                'message'    => 'No active parking session found for this license plate.',
                'alert_type' => 'plate_not_found',
            ], 404);
        }

        // --- 1. PAYMENT & TIME LOGIC FIRST ---
        $isPaymentOk = false;
        $exitType = '';
        $successMessage = '';

        if ($session->status === ParkingStatus::ENTER) {
            $freeMinutes = config('parking.free_exit_minutes', 15);
            
            if (abs(now()->diffInMinutes($session->entry_time)) <= $freeMinutes) {
                // Scenario 1: Free exit eligible
                $isPaymentOk = true;
                $exitType = 'free';
                $successMessage = 'Free exit allowed within 15 minutes.';
            } else {
                // Scenario 2: Unpaid and over 15 mins
                return response()->json([
                    'allowed'   => false,
                    'exit_type' => 'unpaid',
                    'message'   => 'Please pay first via the mobile app.',
                ], 403);
            }
        } elseif ($session->status === ParkingStatus::PAID) {
            // Check grace period
            if ($session->grace_end_time && now()->greaterThan($session->grace_end_time)) {
                $overdueMinutes = $session->grace_end_time->diffInMinutes(now());
                $overdueHours = max(1, ceil($overdueMinutes / 60));
                $extraCharge = $overdueHours * config('parking.rate_per_hour');

                return response()->json([
                    'allowed'         => false,
                    'exit_type'       => 'grace_expired',
                    'message'         => 'Grace period expired. Additional payment required.',
                    'overdue_minutes' => $overdueMinutes,
                    'extra_charge'    => number_format($extraCharge, 2, '.', ''),
                ], 403);
            }

            // Scenario 3: Normal paid exit eligible
            $isPaymentOk = true;
            $exitType = 'normal';
            $successMessage = 'Verification successful. Barrier opened.';
        } else {
            return response()->json(['allowed' => false, 'message' => 'Invalid session state.'], 400);
        }

        // --- 2. ATTRIBUTE MISMATCH LOGIC SECOND ---
        if ($isPaymentOk) {
            $colorMismatch = strtolower($request->color) !== strtolower($session->color);
            $modelMismatch = strtolower($request->model) !== strtolower($session->model);

            if ($colorMismatch || $modelMismatch) {
                // Scenario 5: Attribute mismatch
                $alertType = $colorMismatch ? 'color_mismatch' : 'model_mismatch';
                
                ExitAlert::create([
                    'alert_type'     => $alertType,
                    'license_plate'  => $request->license_plate,
                    'detected_color' => $request->color,
                    'detected_model' => $request->model,
                    'expected_color' => $session->color,
                    'expected_model' => $session->model,
                    'image_path'     => $imagePath,
                    'session_id'     => $session->id,
                ]);

                Log::warning("EXIT VERIFICATION FAILED: {$alertType}", [
                    'license_plate' => $request->license_plate,
                    'session_id'    => $session->id,
                ]);

                return response()->json([
                    'allowed'       => false,
                    'message'       => 'Vehicle attribute mismatch. Admin has been notified.',
                    'alert_type'    => $alertType,
                ], 403);
            }

            // --- 3. FINAL COMPLETION ---
            $session->update([
                'status'    => ParkingStatus::COMPLETED->value,
                'exit_time' => now(),
            ]);

            return response()->json([
                'allowed'   => true,
                'exit_type' => $exitType,
                'message'   => $successMessage,
                'session'   => $session->fresh(),
            ]);
        }
    }
}
