'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Car, Lock, Mail } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { setAuthCookie } from '@/app/actions/auth';
import { Alert, AlertDescription } from '@/components/ui/alert';

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address."),
  password: z.string().min(1, "Password is required.")
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormValues) => {
    setIsLoading(true);
    setError('');

    try {
      const res = await apiFetch('/login', {
        method: 'POST',
        body: JSON.stringify(data)
      });

      if (res.ok) {
        const json = await res.json();
        // Save the Sanctum token strictly in cookies to enable SSR authentication
        await setAuthCookie(json.token);

        // Also keep it in localStorage temporarily for backward compatibility with pure client components
        localStorage.setItem('auth_token', json.token);

        router.push('/dashboard');
      } else {
        const err = await res.json();
        setError(err.message || 'Invalid credentials.');
      }
    } catch {
      setError('An error occurred during login. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1549646452-32a26c48332d?auto=format&fit=crop&q=80')] bg-cover bg-center opacity-[0.03]"></div>

      <div className="w-full max-w-md relative z-10 animate-in zoom-in-95 duration-300">
        <div className="flex justify-center mb-6">
          <div className="bg-primary text-primary-foreground p-3 rounded-2xl shadow-lg">
            <Car className="h-8 w-8" />
          </div>
        </div>

        <Card className="border-0 shadow-xl overflow-hidden">
          <div className="h-2 w-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-2xl font-bold tracking-tight">Welcome Back</CardTitle>
            <CardDescription className="text-base">Sign in to SmartPark Administrator</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">

            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="admin@smartpark.com"
                    className={`pl-10 ${errors.email ? 'border-red-500' : ''}`}
                    {...register('email')}
                  />
                </div>
                {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link href="#" className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    className={`pl-10 ${errors.password ? 'border-red-500' : ''}`}
                    {...register('password')}
                  />
                </div>
                {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
              </div>

              <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 mt-2 h-11" disabled={isLoading}>
                {isLoading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-center border-t py-4 bg-slate-50/50">
            <p className="text-sm text-muted-foreground">
              Don't have an account? <Link href="/register" className="text-indigo-600 font-medium hover:underline">Register</Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
