<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('exit_alerts', function (Blueprint $table) {
            $table->id();
            $table->string('alert_type'); // plate_not_found, color_mismatch, model_mismatch
            $table->string('license_plate');
            $table->string('detected_color')->nullable();
            $table->string('detected_model')->nullable();
            $table->string('expected_color')->nullable();
            $table->string('expected_model')->nullable();
            $table->string('image_path')->nullable();
            $table->foreignId('session_id')->nullable()->constrained('parking_sessions')->onDelete('set null');
            $table->string('status')->default('PENDING'); // PENDING, DISMISSED, OVERRIDDEN
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('exit_alerts');
    }
};
