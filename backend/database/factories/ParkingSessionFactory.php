<?php

namespace Database\Factories;

use App\Enums\ParkingStatus;
use App\Models\ParkingSession;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<ParkingSession>
 */
class ParkingSessionFactory extends Factory
{
    protected $model = ParkingSession::class;

    /**
     * Malaysian state plate prefixes for realistic license plates.
     */
    private const PLATE_PREFIXES = [
        'W', 'WA', 'WB', 'WC', 'WD',          // Kuala Lumpur / Putrajaya
        'V', 'VA', 'VB',                        // Selangor (newer)
        'B', 'BA', 'BB', 'BC', 'BD', 'BH',      // Selangor
        'D', 'DA', 'DB',                         // Perak
        'J', 'JA', 'JB', 'JC', 'JD',            // Johor
        'A', 'AA', 'AB', 'AC',                   // Perak
        'N', 'NA', 'NB',                         // Negeri Sembilan
        'M', 'MA', 'MB',                         // Melaka
        'P', 'PA', 'PB',                         // Penang
        'K', 'KA', 'KB',                         // Kedah
        'T', 'TA', 'TB',                         // Terengganu
        'C', 'CA', 'CB',                         // Pahang
        'R', 'RA', 'RB',                         // Perlis
        'SA', 'SAA', 'SAB',                      // Sabah
        'Q', 'QA', 'QB',                         // Sarawak
    ];

    /**
     * Curated car colors.
     */
    private const COLORS = [
        'White', 'Black', 'Silver', 'Grey', 'Red',
        'Blue', 'Dark Blue', 'Brown', 'Green', 'Gold',
        'Champagne', 'Maroon', 'Orange', 'Yellow',
    ];

    /**
     * Curated car models common in Malaysia.
     */
    private const CAR_MODELS = [
        'Toyota Vios', 'Toyota Camry', 'Toyota Corolla', 'Toyota Hilux',
        'Honda City', 'Honda Civic', 'Honda HR-V', 'Honda CR-V', 'Honda Accord',
        'Perodua Myvi', 'Perodua Axia', 'Perodua Bezza', 'Perodua Ativa', 'Perodua Alza',
        'Proton Saga', 'Proton X50', 'Proton X70', 'Proton Persona', 'Proton Iriz',
        'Nissan Almera', 'Nissan X-Trail', 'Nissan Serena',
        'Mazda 3', 'Mazda CX-5', 'Mazda CX-30',
        'BMW 3 Series', 'BMW X1', 'BMW X3',
        'Mercedes-Benz C-Class', 'Mercedes-Benz A-Class',
        'Hyundai Tucson', 'Hyundai Kona',
        'Kia Seltos', 'Kia Sportage',
        'Mitsubishi Triton', 'Mitsubishi Outlander',
    ];

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        // Generate a realistic Malaysian license plate
        $prefix = $this->faker->randomElement(self::PLATE_PREFIXES);
        $number = $this->faker->numberBetween(1, 9999);
        $suffix = $this->faker->randomElement(['', ' ' . $this->faker->randomLetter()]);
        $licensePlate = strtoupper($prefix . ' ' . $number . $suffix);

        // Generate an entry time within the last 30 days, weighted toward peak hours
        $daysAgo = $this->faker->numberBetween(0, 30);
        $entryDate = now()->subDays($daysAgo);

        // Simulate realistic peak hours: 7-9 AM and 4-7 PM are more common
        $peakHours = $this->faker->randomElement([
            // Morning rush (30% chance)
            ...array_fill(0, 3, $this->faker->numberBetween(7, 9)),
            // Afternoon (20% chance)
            ...array_fill(0, 2, $this->faker->numberBetween(10, 15)),
            // Evening rush (30% chance)
            ...array_fill(0, 3, $this->faker->numberBetween(16, 19)),
            // Off-peak (20% chance)
            ...array_fill(0, 2, $this->faker->numberBetween(20, 23)),
        ]);

        $entryTime = $entryDate->copy()->setTime(
            $peakHours,
            $this->faker->numberBetween(0, 59),
            $this->faker->numberBetween(0, 59)
        );

        // Determine status with weighted distribution
        $status = $this->faker->randomElement([
            ParkingStatus::ENTER,                           // ~20%
            ParkingStatus::PAID, ParkingStatus::PAID,       // ~40%
            ParkingStatus::COMPLETED, ParkingStatus::COMPLETED, // ~40%
        ]);

        // Calculate exit time and amount based on status
        $exitTime = null;
        $amountDue = 0;

        if ($status !== ParkingStatus::ENTER) {
            // Duration between 30 minutes and 8 hours
            $durationMinutes = $this->faker->numberBetween(30, 480);
            $exitTime = $entryTime->copy()->addMinutes($durationMinutes);

            // RM 2.00 per hour, rounded up to nearest hour
            $hours = ceil($durationMinutes / 60);
            $amountDue = $hours * 2.00;
        }

        return [
            'license_plate' => $licensePlate,
            'color'         => $this->faker->randomElement(self::COLORS),
            'model'         => $this->faker->randomElement(self::CAR_MODELS),
            'entry_time'    => $entryTime,
            'exit_time'     => $exitTime,
            'amount_due'    => $amountDue,
            'status'        => $status->value,
        ];
    }

    /**
     * Indicate the session is currently active (car entered, not yet paid/exited).
     */
    public function active(): static
    {
        return $this->state(fn (array $attributes) => [
            'status'     => ParkingStatus::ENTER->value,
            'exit_time'  => null,
            'amount_due' => 0,
        ]);
    }

    /**
     * Indicate the session is paid but car hasn't exited yet.
     */
    public function paid(): static
    {
        return $this->state(function (array $attributes) {
            $entryTime = $attributes['entry_time'];
            $durationMinutes = $this->faker->numberBetween(30, 480);
            $exitTime = $entryTime->copy()->addMinutes($durationMinutes);
            $hours = ceil($durationMinutes / 60);

            return [
                'status'     => ParkingStatus::PAID->value,
                'exit_time'  => $exitTime,
                'amount_due' => $hours * 2.00,
            ];
        });
    }

    /**
     * Indicate the session is fully completed.
     */
    public function completed(): static
    {
        return $this->state(function (array $attributes) {
            $entryTime = $attributes['entry_time'];
            $durationMinutes = $this->faker->numberBetween(30, 480);
            $exitTime = $entryTime->copy()->addMinutes($durationMinutes);
            $hours = ceil($durationMinutes / 60);

            return [
                'status'     => ParkingStatus::COMPLETED->value,
                'exit_time'  => $exitTime,
                'amount_due' => $hours * 2.00,
            ];
        });
    }
}
