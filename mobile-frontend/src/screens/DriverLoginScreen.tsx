import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, ActivityIndicator, Alert } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { ArrowLeft } from 'lucide-react-native';
import apiClient from '../api/client';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'DriverLogin'>;
};

export default function DriverLoginScreen({ navigation }: Props) {
  const insets = useSafeAreaInsets();
  const [licensePlate, setLicensePlate] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCheckPlate = async () => {
    if (!licensePlate.trim()) {
      Alert.alert('Error', 'Please enter your license plate.');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.get(`/parking-sessions/plate/${licensePlate}`);
      const sessionData = response.data;
      
      if (sessionData.status === 'PAID') {
        // Session already paid — check if grace period has expired
        if (sessionData.grace_expired) {
          // Grace expired → additional payment required
          navigation.navigate('AdditionalPayment', { sessionData });
        } else {
          // Grace still active → inform the driver
          const graceEnd = sessionData.grace_end_time
            ? new Date(sessionData.grace_end_time).toLocaleTimeString()
            : 'N/A';
          Alert.alert(
            'Already Paid',
            `You have already paid. Please exit before ${graceEnd}.`
          );
        }
      } else {
        // Status is ENTER → normal payment flow
        navigation.navigate('PaymentDetails', {
          licensePlate,
          sessionData,
        });
      }
    } catch (error: any) {
      if (error.response && error.response.status === 404) {
        Alert.alert('Not Found', 'No active parking session found for this license plate.');
      } else {
        Alert.alert('Error', 'An error occurred while fetching the session details.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="flex-1 bg-white" style={{ paddingTop: insets.top }}>
      {/* Header */}
      <View className="flex-row items-center px-4 py-3">
        <TouchableOpacity className="p-2" onPress={() => navigation.goBack()} disabled={!navigation.canGoBack()}>
          <ArrowLeft size={24} color="#333" />
        </TouchableOpacity>
        <Text className="font-interBold text-lg ml-2 text-gray-800">Driver Login</Text>
      </View>

      {/* Main Content */}
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'} 
        className="flex-1 px-6 justify-center"
      >
        <View className="w-full">
          <Text className="font-manrope text-[28px] font-bold text-gray-900 mb-2">
            Parking User Login
          </Text>
          <Text className="font-inter text-[16px] text-[#666666] mb-8">
            Enter your license plate to pay
          </Text>

          <View className="mb-6">
            <TextInput
              className="w-full h-[56px] border border-[#cccccc] rounded-lg px-4 text-[16px] font-inter text-gray-900 bg-white"
              placeholder="ABC1234"
              placeholderTextColor="#999"
              value={licensePlate}
              onChangeText={setLicensePlate}
              autoCapitalize="characters"
              autoCorrect={false}
            />
          </View>

          <TouchableOpacity
            className="w-full h-[56px] bg-[#007BFF] rounded-lg items-center justify-center shadow-sm"
            style={{
              shadowColor: '#007BFF',
              shadowOffset: { width: 0, height: 4 },
              shadowOpacity: 0.2,
              shadowRadius: 8,
              elevation: 4,
            }}
            onPress={handleCheckPlate}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text className="font-interBold text-white text-[16px]">Check Plate</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}
