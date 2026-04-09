'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { apiFetch } from '@/lib/api';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { CheckCircle2, User, Mail, Lock } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function ProfileForm() {
  const [user, setUser] = useState({ name: '', email: '' });
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await apiFetch('/user');
        if (res.ok) {
          const data = await res.json();
          setUser({ name: data.name, email: data.email });
        }
      } catch (e) {
        setUser({ name: 'Admin', email: 'admin@smartpark.com' });
      }
    };
    fetchUser();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password && password !== confirmPassword) {
      setStatus('error');
      return;
    }

    setStatus('saving');
    
    try {
      const payload: any = { name: user.name, email: user.email };
      if (password) payload.password = password;

      const res = await apiFetch('/user/profile', {
        method: 'PUT',
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        setStatus('success');
        setPassword('');
        setConfirmPassword('');
        setTimeout(() => setStatus('idle'), 3000);
      } else {
        setStatus('error');
      }
    } catch {
      setStatus('error');
    }
  };

  return (
    <div className="p-6 md:p-8 flex-1 space-y-6 bg-slate-50 min-h-[calc(100vh-64px)] animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Admin Profile</h1>
        <p className="text-muted-foreground mt-1">
          Manage your account settings and system preferences.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 max-w-5xl">
        <Card className="md:col-span-1 shadow-sm border-gray-200">
          <CardContent className="flex flex-col items-center pt-6">
            <Avatar className="h-24 w-24 border-4 border-indigo-50 mb-4">
              <AvatarImage src="https://i.pravatar.cc/150?u=admin" alt="Admin Avatar" />
              <AvatarFallback className="text-2xl bg-indigo-100 text-indigo-700 font-bold">AD</AvatarFallback>
            </Avatar>
            <h3 className="font-semibold text-lg">{user.name || 'Administrator'}</h3>
            <p className="text-sm text-muted-foreground">{user.email || 'admin@smartpark.com'}</p>
            <span className="mt-3 inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 border-none">System Admin</span>
          </CardContent>
        </Card>

        <Card className="md:col-span-2 shadow-sm border-gray-200 overflow-hidden">
          <form onSubmit={handleSave}>
            <CardHeader className="bg-white border-b">
              <CardTitle>Account Details</CardTitle>
              <CardDescription>Update your personal information and security details.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-6 pb-6 bg-white">
              
              {status === 'success' && (
                <Alert className="bg-green-50 border-green-200 text-green-800 py-3 mb-4">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <AlertDescription>Profile updated successfully.</AlertDescription>
                </Alert>
              )}
              {status === 'error' && (
                <Alert variant="destructive" className="py-3 mb-4">
                  <AlertDescription>Failed to update profile. Ensure passwords match.</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="name" className="flex items-center gap-2"><User className="h-4 w-4 text-gray-400"/> Full Name</Label>
                <Input 
                  id="name" 
                  value={user.name} 
                  onChange={(e) => setUser({...user, name: e.target.value})} 
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2"><Mail className="h-4 w-4 text-gray-400"/> Email Address</Label>
                <Input 
                  id="email" 
                  type="email" 
                  value={user.email} 
                  onChange={(e) => setUser({...user, email: e.target.value})} 
                  required
                />
              </div>

              <div className="pt-4 border-t mt-6">
                <h4 className="text-sm font-semibold mb-4 text-gray-900">Change Password (Optional)</h4>
                
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="password" className="flex items-center gap-2"><Lock className="h-4 w-4 text-gray-400"/> New Password</Label>
                    <Input 
                      id="password" 
                      type="password" 
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Leave blank to keep current" 
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm_password">Confirm Password</Label>
                    <Input 
                      id="confirm_password" 
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                  </div>
                </div>
              </div>

            </CardContent>
            <CardFooter className="bg-slate-50 border-t px-6 py-4 justify-end">
              <Button type="submit" disabled={status === 'saving'} className="bg-indigo-600 hover:bg-indigo-700">
                {status === 'saving' ? 'Saving...' : 'Save Changes'}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
